#!/usr/bin/env python3
"""Compile the source CSVs into data.json for the browser.

The CSVs (the roster pair, plus the family pair in family/) are the source of
truth; data.json is a build artifact. Run this after editing any CSV, then
commit both.

    python3 build.py

This script owns the tie definitions. index.html only draws what it is given
and filters edges down to the visible node set, so the co-tenure rule lives in
exactly one place.
"""

import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date

GENERAL_CSV = "Kazakhstan Elite Monitoring  - General.csv"
POSITIONS_CSV = "Kazakhstan Elite Monitoring  - Positions.csv"
OUT = "data.json"

# Relatives of one roster member, kept apart from the roster in the same two
# CSV shapes plus link columns. Rows key on F-codes, which become ids above
# FAMILY_ID_OFFSET so they can never collide with a P-number. Each relative
# gets a family edge to the anchor, labelled with the relationship.
FAMILY_GENERAL_CSV = "family/Tokayev Family Monitoring - General.csv"
FAMILY_POSITIONS_CSV = "family/Tokayev Family Monitoring - Positions.csv"
FAMILY_ANCHOR = "P001"
FAMILY_ID_OFFSET = 1000
FAMILY_KINDS = {"blood", "marriage", "inlaw", "former"}

# An open-ended stint has to resolve to a concrete year before its overlaps can
# be computed. The browser used to do this with new Date().getFullYear(), so the
# graph silently changed from year to year; pinning it at build time makes the
# dataset reproducible, and meta.buildYear records which year that was.
#
# Only the edge computation resolves it. workExperience keeps the literal
# "Present" so career histories still read "2025–Present" rather than a year
# that looks like the post already ended.
BUILD_YEAR = date.today().year
PRESENT = "Present"


def die(msg):
    sys.exit(f"build.py: {msg}")


def person_num(pid):
    """P001 -> 1. The CSVs key on P-codes, the JSON on integers."""
    m = re.fullmatch(r"P0*(\d+)", (pid or "").strip())
    return int(m.group(1)) if m else None


def family_num(pid):
    """F005 -> 1005, the family CSVs' counterpart of person_num."""
    m = re.fullmatch(r"F0*(\d+)", (pid or "").strip())
    return FAMILY_ID_OFFSET + int(m.group(1)) if m else None


def clean(s):
    return (s or "").strip()


# School and region ties are exact string matches, so the spelling of a value
# *is* part of the tie definition and has to be normalised before grouping.
# Previously this cleanup happened somewhere outside the repo, which is why the
# CSVs and the old data.json disagreed. It is written down here instead.

# Placeholders for "we don't know". Left as-is they would group every unknown
# person together into one large spurious clique, so they become missing.
MISSING_VALUES = {"", "unknown", "n/a", "na", "none", "-", "?"}

# Spellings of one place/school that must be folded together before grouping.
# Prefer fixing the CSV; add an entry here only for a variant that is genuinely
# correct as written and so cannot be edited away.
ALIASES = {
    "region": {},
    "school": {},
}

# A region cell sometimes names the specific city or district
# ("Turkestan Region (Otyrar district)"). The analytical unit is the region, so
# the parenthetical is dropped for grouping purposes.
PARENTHETICAL = re.compile(r"\s*\([^)]*\)\s*$")


def normalize(value, field):
    v = clean(value)
    if v.lower() in MISSING_VALUES:
        return ""
    if field == "region":
        v = PARENTHETICAL.sub("", v).strip()
    return ALIASES.get(field, {}).get(v, v)


def year_of(v):
    """Concrete year for a stored year value; "Present" runs to the build year."""
    return BUILD_YEAR if v == PRESENT else v


def read_rows(path):
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            # Header fields carry stray spaces and a typo ("Current Instution");
            # normalising here keeps the lookups below readable.
            reader = csv.DictReader(fh)
            reader.fieldnames = [clean(f) for f in (reader.fieldnames or [])]
            return list(reader)
    except FileNotFoundError:
        die(f"missing {path}")


def build_people(rows, warn, id_of=person_num, path=GENERAL_CSV):
    people, seen = [], set()
    for i, r in enumerate(rows, start=2):  # row 1 is the header
        pid = id_of(r.get("Id"))
        if pid is None:
            if any(clean(v) for v in r.values()):
                warn(f"{path} row {i}: unparseable Id {r.get('Id')!r}, skipped")
            continue  # blank spacer rows are expected
        if pid in seen:
            die(f"{path} row {i}: duplicate Id {r.get('Id')}")
        seen.add(pid)

        age = clean(r.get("Age"))
        people.append({
            "id": pid,
            "name": clean(r.get("Name")),
            "age": int(age) if age.isdigit() else None,
            "role": clean(r.get("Current_Role")),
            "institution": normalize(r.get("Current Instution"), "institution"),
            "region": normalize(r.get("Birth Region"), "region"),
            "school": normalize(r.get("School"), "school"),
            "zhuz": normalize(r.get("Zhuz"), "zhuz"),
            "category": clean(r.get("Institutional Identity")),
        })
    people.sort(key=lambda p: p["id"])
    return people


def parse_year(v, row_no, warn, path=POSITIONS_CSV):
    """Years are ints, or the string "Present" for an open-ended stint."""
    v = clean(v)
    if not v:
        return None
    if v.lower() == "present":
        return PRESENT
    if re.fullmatch(r"-?\d{4}", v):
        return int(v)
    # Many cells carry a full date (24.03.2019) or month and year (7.2016).
    # Tenure is only ever resolved to the year, so take it and stay quiet —
    # warning on every one of these buries the warnings that matter.
    m = re.fullmatch(r"\d{1,2}\.(?:\d{1,2}\.)?(\d{4})", v)
    if m:
        return int(m.group(1))
    m = re.search(r"\d{4}", v)  # anything else with a year in it: say so
    if m:
        warn(f"{path} row {row_no}: read year {v!r} as {m.group(1) if m.groups() else m.group(0)}")
        return int(m.group(0))
    warn(f"{path} row {row_no}: unreadable year {v!r}, treated as blank")
    return None


def build_work(rows, valid_ids, warn, id_of=person_num, path=POSITIONS_CSV):
    work = []
    for i, r in enumerate(rows, start=2):
        pid = id_of(r.get("Person_ID"))
        if pid is None:
            if any(clean(v) for v in r.values()):
                warn(f"{path} row {i}: unparseable Person_ID, skipped")
            continue
        if pid not in valid_ids:
            # A position pointing at nobody is a data error, not a spacer row.
            warn(f"{path} row {i}: Person_ID {r.get('Person_ID')} has no person row, skipped")
            continue

        start = parse_year(r.get("Start_Year"), i, warn, path)
        end = parse_year(r.get("End_Year"), i, warn, path)
        if isinstance(start, int) and isinstance(end, int) and start > end:
            warn(f"{path} row {i}: start {start} after end {end}")

        # A joint appointment ("Deputy PM; Minister of Foreign Affairs") lists
        # both institutions in one cell. Split it: the person genuinely served
        # at each, and each should generate its own co-tenure ties.
        institutions = [x for x in
                        (clean(part) for part in clean(r.get("Institution")).split(";"))
                        if x] or [""]
        for inst in institutions:
            work.append({
                "personId": pid,
                "title": clean(r.get("Title")),
                "institution": inst,
                "startYear": start,
                "endYear": end,
                "source": clean(r.get("Source")),
            })
    work.sort(key=lambda w: (w["personId"], year_of(w["startYear"]) or 0))
    return work


IN_OFFICE = "In office"
OUT_OF_GOVERNMENT = "Out of government"


def mark_status(people, work):
    """In office, or out of government (e.g. dismissed, next post unknown).

    Derived rather than hand-coded: someone with no open-ended ("Present")
    stint holds no current post we know of. This is a separate axis from the
    institutional identity, which follows the career track and so stays put
    when a person leaves office.
    """
    current = {w["personId"] for w in work if w["endYear"] == PRESENT}
    for p in people:
        p["status"] = IN_OFFICE if p["id"] in current else OUT_OF_GOVERNMENT


def attribute_edges(people, field, etype):
    """Link everyone sharing an exact attribute value (school, birth region)."""
    groups = defaultdict(list)
    for p in people:
        if p[field]:
            groups[p[field]].append(p["id"])

    label = {"school": "Same school", "region": "Same region"}[etype]
    edges = []
    for value, ids in groups.items():
        ids.sort()
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                edges.append({
                    "id": f"{etype}:{ids[i]}-{ids[j]}",
                    "from": ids[i], "to": ids[j], "ltype": etype,
                    "title": f"{label}: {value}",
                })
    return edges


def merge_ranges(ranges):
    """Collapse overlapping/adjacent year spans into a display string."""
    ranges.sort()
    out = []
    for s, e in ranges:
        if out and s <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return ", ".join(str(s) if s == e else f"{s}–{e}" for s, e in out)


# Labels used when a bio names no specific unit ("platoon commander to unit
# commander, 1998-2018"). Two people filed under one of these were not
# necessarily ever in the same place, so they would link for decades on the
# strength of what the bios leave out. Their stints still show in career
# histories; they just never create a workplace tie. Rows whose bio does name
# the unit are filed under that unit instead.
CATCH_ALL_INSTITUTIONS = {
    "Armed Forces",
    "Ground Forces",
    "Military Police",
    "National Security Committee (KNB)",
}


def workplace_edges(work):
    """Co-tenure: same institution, overlapping years.

    Boundary years count as an overlap (one person arriving the year another
    leaves). Same employer in disjoint eras does not connect.
    """
    by_inst = defaultdict(list)
    for w in work:
        if not w["institution"] or w["institution"] in CATCH_ALL_INSTITUTIONS:
            continue
        s, e = year_of(w["startYear"]), year_of(w["endYear"])
        if s is None and e is None:
            continue  # undated stint cannot be placed in time
        s = e if s is None else s
        e = s if e is None else e
        by_inst[w["institution"]].append((w["personId"], s, e))

    shared = defaultdict(lambda: defaultdict(list))
    for inst, stints in by_inst.items():
        for i in range(len(stints)):
            for j in range(i + 1, len(stints)):
                a, a_s, a_e = stints[i]
                b, b_s, b_e = stints[j]
                if a == b:
                    continue  # two stints of one person at one institution
                os_, oe = max(a_s, b_s), min(a_e, b_e)
                if os_ > oe:
                    continue
                shared[(min(a, b), max(a, b))][inst].append([os_, oe])

    edges = []
    for (a, b), insts in shared.items():
        label = "; ".join(
            f"{inst} ({merge_ranges(rs)})" for inst, rs in sorted(insts.items())
        )
        edges.append({
            "id": f"work:{a}-{b}", "from": a, "to": b, "ltype": "work",
            "title": f"Shared workplace: {label}",
        })
    return edges


def family_edges(rows, anchor, warn):
    """One labelled edge from each relative to the family's anchor.

    Link_Type holds the kind of tie (blood, marriage, inlaw), plus "former"
    for one that has ended; the browser styles each kind differently.
    """
    edges = []
    for i, r in enumerate(rows, start=2):
        fid = family_num(r.get("Id"))
        if fid is None:
            continue  # build_people has already reported the row
        label = clean(r.get("Link_Label"))
        kinds = clean(r.get("Link_Type")).lower().split()
        if not label:
            warn(f"{FAMILY_GENERAL_CSV} row {i}: no Link_Label, family edge skipped")
            continue
        if not kinds or set(kinds) - FAMILY_KINDS:
            warn(f"{FAMILY_GENERAL_CSV} row {i}: Link_Type {r.get('Link_Type')!r} "
                 f"should be from {sorted(FAMILY_KINDS)}")
        edges.append({
            "id": f"family:{fid}-{anchor}", "from": fid, "to": anchor, "ltype": "family",
            "kind": [k for k in kinds if k in FAMILY_KINDS],
            "label": label,
            "title": f"Family: {clean(r.get('Relationship_to_Tokayev')) or label}",
        })
    return edges


def check_near_duplicates(people, warn):
    """Flag values that look like the same place/school spelled two ways.

    School and region ties are exact matches, so "Shymkent" and "Shymkent City"
    are two unrelated groups and the people in them never link. That failure is
    invisible in the finished graph — it shows up as absent edges, not as an
    error — so it is worth catching here.
    """
    for field in ("region", "school"):
        values = sorted({p[field] for p in people if p[field]})
        for a in values:
            for b in values:
                if a != b and b.startswith(a + " "):
                    warn(f"{field}: {a!r} and {b!r} will not link — same place spelled two ways?")


def main():
    warnings = []
    warn = warnings.append

    people = build_people(read_rows(GENERAL_CSV), warn)
    if not people:
        die(f"no people parsed from {GENERAL_CSV}")
    anchor = person_num(FAMILY_ANCHOR)
    if anchor not in {p["id"] for p in people}:
        die(f"family anchor {FAMILY_ANCHOR} is not in {GENERAL_CSV}")

    # Relatives join the graph as ordinary people, so their careers, schools
    # and regions tie into the roster by the same rules; "family" marks them
    # so the browser can show or hide them with their family links.
    family_rows = read_rows(FAMILY_GENERAL_CSV)
    family = build_people(family_rows, warn, family_num, FAMILY_GENERAL_CSV)
    relationship = {family_num(r.get("Id")): clean(r.get("Relationship_to_Tokayev")) for r in family_rows}
    for p in family:
        p["family"] = True
        p["relationship"] = relationship[p["id"]]
    people += family

    check_near_duplicates(people, warn)
    work = (build_work(read_rows(POSITIONS_CSV), {p["id"] for p in people if not p.get("family")}, warn)
            + build_work(read_rows(FAMILY_POSITIONS_CSV), {p["id"] for p in family}, warn,
                         family_num, FAMILY_POSITIONS_CSV))
    work.sort(key=lambda w: (w["personId"], year_of(w["startYear"]) or 0))
    mark_status(people, work)

    edges = (workplace_edges(work)
             + attribute_edges(people, "school", "school")
             + attribute_edges(people, "region", "region")
             + family_edges(family_rows, anchor, warn))
    edges.sort(key=lambda e: (e["ltype"], e["from"], e["to"]))

    data = {
        "meta": {
            "builtBy": "build.py",
            "buildYear": BUILD_YEAR,
            "note": "Generated from the CSVs; edit those, not this file. "
                    f"Open-ended ('Present') stints run through {BUILD_YEAR}.",
        },
        "people": people,
        "workExperience": work,
        "edges": edges,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    by_type = defaultdict(int)
    for e in edges:
        by_type[e["ltype"]] += 1
    print(f"{OUT}: {len(people)} people ({len(family)} family), {len(work)} positions, "
          f"{len(set(w['institution'] for w in work if w['institution']))} institutions")
    print(f"  edges: {len(edges)} total — "
          + ", ".join(f"{k} {v}" for k, v in sorted(by_type.items())))
    if warnings:
        print(f"\n{len(warnings)} data warning(s):", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
