# Elite Network Monitor

An interactive, browser-based **one-mode people network**. Two people are linked when they share an attribute you choose — a workplace (from career history), a school, or a region. Filter which people appear, toggle which link types are drawn, click a node to see the full profile. No backend: two files, works on GitHub Pages.


## How the links work

- **Workplace (career history)** — links two people if any institution appears in *both* their `workExperience`. This is the elite-tie signal: same employer at some point, not just today.
- **School** — links people with the same `school`.
- **Region** — links people with the same `region`.


