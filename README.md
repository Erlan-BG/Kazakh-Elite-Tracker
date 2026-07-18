# Kazakh Elite Tracker

**https://erlan-bg.github.io/Kazakh-Elite-Tracker/>**

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

Two hand-built CSVs are the source of truth; `data.json` is compiled from them
for the browser.

| File | Contents |
| --- | --- |
| `Kazakhstan Elite Monitoring  - General.csv` | One row per person (n = 70): name, age, current role and institution, birth region, school, zhuz, institutional-identity coding |
| `Kazakhstan Elite Monitoring  - Positions.csv` | One row per career stint (616 records, 191 distinct institutions, 1986–present): title, institution, start/end year, source URL |

Career histories are compiled from official biographies (Akorda, ministry and
akimat sites) and public reporting; a `Source` column records the URL for each
position where one exists. Zhuz affiliation is coded for all 70 individuals
from public genealogical and journalistic sources.

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
- **Coarse time resolution.** Tenure is recorded in years, so two officials who
  overlapped for one month in the same calendar year still link.

## Running locally

No build step. Clone and open `index.html` in a browser, or serve the folder:

```bash
python3 -m http.server 8000
# → http://localhost:8000
```

## Roadmap

- Centrality measures (degree, betweenness) surfaced in the UI — who brokers
  between the silovik and technocrat clusters?
- Time slider: replay the network year by year, before and after January 2022.
- Expand per-position source coverage to 100%.
