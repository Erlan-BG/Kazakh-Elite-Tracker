# Elite Network Monitor

An interactive, browser-based **one-mode people network**. Two people are linked when they share an attribute you choose — a workplace (from career history), a school, or a region. Filter which people appear, toggle which link types are drawn, click a node to see the full profile. No backend: two files, works on GitHub Pages.


## How the links work

- **Workplace (overlapping tenure)** — links two people only if they were at the *same institution at the same time*: their `workExperience` stints must share at least one year (boundary years count; `Present` runs through the current year). Same employer in disjoint eras — e.g. KNB 1997–2001 vs KNB 2007–2017 — does **not** connect. Embassies and other foreign postings are distinct institutions from the MFA headquarters, so an ambassador abroad does not link to ministry staff at home.
- **School** — links people with the same `school`.
- **Region** — links people with the same `region`.


