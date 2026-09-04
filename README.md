# Kazakh Elite Tracker

**Live demo: <https://erlan-bg.github.io/Kazakh-Elite-Tracker/>**

An interactive network map of Kazakhstan's political elite. 70 senior officials —
akims, ministers, KNB leadership, presidential administration, heads of state
institutions — connected by the career, educational, and regional ties that the
Central Asia literature treats as the skeleton of patronage politics. Toggle
which shared attributes draw links, filter who appears, click any node for a
full sourced career history. No backend: a single HTML file plus a JSON dataset,
served straight from GitHub Pages.

![Elite Network Monitor — full network, all link types on. Node color is institutional identity (diplomat, technocrat, silovik, akimat, …); node size is degree.](screenshot.png)

## Why these ties

A formal org chart tells you little about how power works in Kazakhstan;
scholars of the region argue that politics runs through informal networks
built on shared careers, schools, and home regions (Collins and Schatz on clan
politics; Hale on patronal politics). This tool operationalizes that claim:
each link type is one hypothesized channel of affiliation, and each can be
switched on or off independently to see which structure it produces.

- **Workplace (overlapping tenure)** — the strictest tie. Two people are linked
  only if they served at the *same institution at the same time*: their career
  stints must share at least one calendar year (boundary years count; `Present`
  runs through the current year). Same employer in disjoint eras — KNB
  1997–2001 vs. KNB 2007–2017 — does **not** connect. Embassies and other
  foreign postings are distinct institutions from the MFA headquarters, so an
  ambassador abroad does not link to ministry staff at home.
- **School** — a shared alma mater, the classic site of early network
  formation.
- **Region** — a shared birth region, the standard observable proxy for
  regional patronage affiliation.

Node color encodes an **institutional identity** coding (diplomat, technocrat,
bureaucrat, ideologue, state-security/silovik, akimat, politician) assigned
from each person's dominant career track.

## Data

Two hand-built CSVs are the source of truth; `data.json` is a build artifact
compiled from them by `build.py` (see [Building the data](#building-the-data)).
Edit the CSVs, never `data.json`.

| File | Contents |
| --- | --- |
| `Kazakhstan Elite Monitoring  - General.csv` | One row per person (n = 70): name, age, current role and institution, birth region, school, zhuz, institutional-identity coding |
| `Kazakhstan Elite Monitoring  - Positions.csv` | One row per career stint (616 records, 191 distinct institutions, 1986–present): title, institution, start/end year, source URL |

Career histories are compiled from official biographies (Akorda, ministry and
akimat sites) and public reporting; a `Source` column records the URL for each
position where one exists. Zhuz affiliation is coded for 3 of 70 individuals
so far, from public genealogical and journalistic sources; coding the rest is
ongoing (see Limitations).

## Limitations, stated plainly

- **Informal ties are invisible.** Family, marriage, and business relationships
  — arguably the most important elite ties in Kazakhstan — do not appear in
  official biographies and are not captured here. Co-tenure is a *proxy* for
  acquaintance, not proof of alliance.
- **Selection.** The 70 people are the current senior cohort, not a random
  sample; network statistics describe this roster, not the elite as a whole.
- **Source coverage is partial.** Roughly 40% of position records currently
  carry an explicit source URL; the rest trace to official bios pending
  citation. Official biographies themselves omit inconvenient episodes.
- **Zhuz coverage is mostly incomplete.** Only 3 of 70 people are coded; the
  rest are `Unknown`. Not enough to support any zhuz-based network analysis
  yet — treat the field as a placeholder for ongoing research, not a
  finished attribute.
- **Coarse time resolution.** Tenure is recorded in years, so two officials who
  overlapped for one month in the same calendar year still link.

## Running locally

Clone and open `index.html` in a browser, or serve the folder:

```bash
python3 -m http.server 8000
# → http://localhost:8000
```

## Building the data

`build.py` compiles the two CSVs into `data.json`. Edit the CSVs, then:

```bash
python3 build.py     # standard library only, no dependencies
```

It reports counts and prints data warnings to stderr (unreadable years,
positions pointing at a person who isn't in the roster, start after end).

The script owns the **tie definitions** — co-tenure overlap, shared school,
shared birth region — and writes the resulting edge list into `data.json`.
`index.html` only draws what it is given, filtering that edge list down to the
people and link types currently selected. Betweenness and Louvain communities
stay in the browser, because both are computed on whatever subgraph is on
screen rather than on the full network.

Two consequences worth knowing:

- **Open-ended stints are pinned at build time.** `Present` resolves to the
  year the build ran, recorded as `meta.buildYear`, so the graph no longer
  changes silently as the calendar advances. Career histories still *display*
  "Present". Rebuild to roll it forward.
- **Normalisation is part of the tie definition.** Since school and region
  links are exact string matches, spelling variants break ties and placeholders
  invent them — ten people with region `Unknown` would otherwise form a
  45-edge clique of strangers. `build.py` drops placeholder values and trims
  the city/district parenthetical from region names (`Turkestan Region
  (Kentau)` → `Turkestan Region`), which is the deliberate choice to treat the
  region as the analytical unit.

  Outright misspellings are fixed in the CSVs instead, so the alias table in
  `build.py` is empty by design. Because a variant spelling fails *silently* —
  it shows up as a missing edge, never as an error — the build warns when one
  value is a prefix of another (`Shymkent` alongside `Shymkent City`). Take
  those warnings seriously; that pair alone was worth two region ties.

## Roadmap

- ~~Centrality measures (degree, betweenness) surfaced in the UI~~ — done;
  see the Analysis panel.
- **Time slider: replay the network year by year**, before and after January
  2022. The per-pair overlap ranges this needs are already computed inside
  `build.py`'s `workplace_edges()`; they just aren't emitted per-year yet.
  Needs one design call first: does a given year show ties *active in* that
  year, or ties *formed by* it (cumulative) — the two produce different
  networks and change what "before vs. after 2022" means.
- Validate the browser's hand-rolled betweenness (Brandes, in `index.html`)
  against a reference implementation — `networkx` or R's `igraph` — on a few
  fixed, unfiltered link configurations. Confirms the published centrality
  numbers are correct; a one-off script, not a permanent dependency.
- Guard against `data.json` silently going stale relative to the CSVs now
  that they're no longer the same file — a pre-commit hook or CI check that
  fails if `build.py`'s output differs from what's committed.
- Expand per-position source coverage to 100%.
