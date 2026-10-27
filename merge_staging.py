#!/usr/bin/env python3
"""Check staged rows and merge them into the main CSVs.

New people and new career stints are drafted in staging/ first, reviewed,
then merged in one step:

    python3 merge_staging.py           # dry run: check and show the plan
    python3 merge_staging.py --apply   # append to the main CSVs, rebuild

staging/persons.csv   new people. Id is a temporary key (NEW-1, NEW-2, ...);
                      real P-numbers are assigned at merge time.
staging/positions.csv career stints. Person_ID is either a temporary key from
                      staging/persons.csv or an existing P-number, so this
                      file also adds new stints to people already tracked.

Merging is append-only. Changing an existing row (closing a stint that ended,
correcting a value) is done directly in the main CSVs.
"""

import csv
import difflib
import re
import subprocess
import sys

import build
from build import GENERAL_CSV, POSITIONS_CSV, PRESENT, clean, normalize, person_num

STAGED_PERSONS = "staging/persons.csv"
STAGED_POSITIONS = "staging/positions.csv"
TEMP_KEY = re.compile(r"NEW-\d+", re.IGNORECASE)


def read_raw(path):
    """Header exactly as written, plus rows keyed by the cleaned header."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = next(reader, [])
        keys = [clean(h) for h in header]
        rows = [dict(zip(keys, r)) for r in reader]
    return header, [r for r in rows if any(clean(v) for v in r.values())]


def closest(value, choices):
    match = difflib.get_close_matches(value, choices, n=1, cutoff=0.75)
    return f" (closest existing: {match[0]!r})" if match else ""


def name_key(name):
    return " ".join(clean(name).lower().split())


def check(errors, warnings):
    """Validate staging against the main CSVs. Returns the merge plan."""
    _, people = read_raw(GENERAL_CSV)
    _, stints = read_raw(POSITIONS_CSV)
    _, staged_people = read_raw(STAGED_PERSONS)
    _, staged_stints = read_raw(STAGED_POSITIONS)

    existing = {person_num(p["Id"]): p for p in people if person_num(p["Id"])}
    names = {name_key(p["Name"]): pid for pid, p in existing.items()}
    categories = {clean(p["Institutional Identity"]) for p in existing.values()} - {""}
    regions = sorted({normalize(p["Birth Region"], "region") for p in existing.values()} - {""})
    schools = sorted({normalize(p["School"], "school") for p in existing.values()} - {""})
    institutions = sorted({clean(s["Institution"]) for s in stints} - {""})

    # --- people ---------------------------------------------------------
    temp = {}  # NEW-n -> staged person row
    for i, p in enumerate(staged_people, start=2):
        where = f"{STAGED_PERSONS} row {i}"
        key, name = clean(p.get("Id")), clean(p.get("Name"))

        if not TEMP_KEY.fullmatch(key):
            errors.append(f"{where}: Id must be a temporary key like NEW-1, got {key!r}"
                          + (" (existing people are edited in the main CSV)" if person_num(key) else ""))
            continue
        key = key.upper()
        if key in temp:
            errors.append(f"{where}: Id {key} used twice")
            continue
        if not name:
            errors.append(f"{where}: Name is empty")
        elif name_key(name) in names:
            errors.append(f"{where}: {name!r} is already P{names[name_key(name)]:03d}")
        else:
            # Transliteration drift (Ergeshbayev / Yergeshbayev) slips past an
            # exact check and would silently create a duplicate person.
            similar = difflib.get_close_matches(name_key(name), list(names), n=1, cutoff=0.85)
            if similar:
                warnings.append(f"{where}: {name!r} looks like existing "
                                f"P{names[similar[0]]:03d} {existing[names[similar[0]]]['Name']!r} — same person?")

        category = clean(p.get("Institutional Identity"))
        if category not in categories:
            errors.append(f"{where}: Institutional Identity {category!r} is not one of "
                          f"{sorted(categories)}")

        # Region and school ties are exact matches, so a new spelling of an
        # existing value drops ties without any error. Flag every new value.
        for field, col, known in (("region", "Birth Region", regions), ("school", "School", schools)):
            v = normalize(p.get(col), field)
            if v and v not in known:
                warnings.append(f"{where}: new {field} {v!r}{closest(v, known)}")

        age = clean(p.get("Age"))
        if age and not age.isdigit():
            errors.append(f"{where}: Age {age!r} is not a whole number")

        temp[key] = p

    # --- positions ------------------------------------------------------
    staged_for = {k: 0 for k in temp}
    for i, s in enumerate(staged_stints, start=2):
        where = f"{STAGED_POSITIONS} row {i}"
        ref = clean(s.get("Person_ID")).upper()

        if ref in temp:
            staged_for[ref] += 1
        elif person_num(ref) not in existing:
            errors.append(f"{where}: Person_ID {ref!r} is neither a staged NEW-n key "
                          "nor an existing person")

        for col in ("Title", "Institution"):
            if not clean(s.get(col)):
                errors.append(f"{where}: {col} is empty")
        # Staged rows are drafts until checked against a source, so the
        # source travels with the row rather than being added later.
        if not clean(s.get("Source")):
            errors.append(f"{where}: Source is empty — every staged stint needs one")

        msgs = []
        start = build.parse_year(s.get("Start_Year"), i, msgs.append)
        end = build.parse_year(s.get("End_Year"), i, msgs.append)
        for m in msgs:
            errors.append(f"{where}: {m.split(': ', 1)[-1]}")
        if start is None and end is None:
            errors.append(f"{where}: no usable Start_Year or End_Year")
        elif start == PRESENT:
            errors.append(f"{where}: Start_Year cannot be {PRESENT!r}")
        elif isinstance(start, int) and isinstance(end, int) and start > end:
            errors.append(f"{where}: Start_Year {start} is after End_Year {end}")

        for inst in filter(None, (clean(x) for x in clean(s.get("Institution")).split(";"))):
            if inst not in institutions:
                warnings.append(f"{where}: new institution {inst!r}{closest(inst, institutions)} "
                                "— co-tenure only links identical names")

    for key, count in staged_for.items():
        if not count:
            warnings.append(f"{STAGED_PERSONS}: {key} {clean(temp[key].get('Name'))!r} "
                            "has no staged positions and will have no workplace ties")

    next_id = max(existing) + 1
    ids = {key: f"P{next_id + n:03d}" for n, key in enumerate(temp)}
    return temp, staged_stints, ids, existing


def append(path, header, rows):
    keys = [clean(h) for h in header]
    with open(path, "rb") as fh:
        fh.seek(-1, 2)
        needs_newline = fh.read(1) not in (b"\n", b"\r")
    with open(path, "a", newline="", encoding="utf-8") as fh:
        if needs_newline:
            fh.write("\r\n")
        writer = csv.writer(fh)
        for r in rows:
            writer.writerow([r.get(k, "") for k in keys])


def reset(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        header = fh.readline()
    with open(path, "w", newline="", encoding="utf-8") as fh:
        fh.write(header)


def main():
    apply = "--apply" in sys.argv[1:]
    errors, warnings = [], []
    temp, staged_stints, ids, existing = check(errors, warnings)

    if not temp and not staged_stints:
        print("Staging is empty — nothing to merge.")
        return

    print(f"{len(temp)} new people, {len(staged_stints)} new positions staged.\n")
    for key, new_id in ids.items():
        print(f"  {key} -> {new_id}  {clean(temp[key].get('Name'))}")
    for w in warnings:
        print(f"  warning: {w}")
    if errors:
        sys.stdout.flush()
        print(f"\n{len(errors)} error(s) — nothing merged:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    if not apply:
        print("\nDry run. Review the warnings, then: python3 merge_staging.py --apply")
        return

    new_people = []
    for key, p in temp.items():
        new_people.append({**p, "Id": ids[key]})

    new_stints = []
    for s in staged_stints:
        ref = clean(s.get("Person_ID")).upper()
        if ref in ids:
            pid, name = ids[ref], clean(temp[ref].get("Name"))
        else:
            pid = f"P{person_num(ref):03d}"
            name = clean(existing[person_num(ref)].get("Name"))
        new_stints.append({**s, "Person_ID": pid, "Name": name})

    general_header, _ = read_raw(GENERAL_CSV)
    positions_header, _ = read_raw(POSITIONS_CSV)
    append(GENERAL_CSV, general_header, new_people)
    append(POSITIONS_CSV, positions_header, new_stints)
    reset(STAGED_PERSONS)
    reset(STAGED_POSITIONS)
    print(f"\nMerged into the main CSVs; staging cleared. Rebuilding:\n", flush=True)
    subprocess.run([sys.executable, "build.py"], check=True)


if __name__ == "__main__":
    main()
