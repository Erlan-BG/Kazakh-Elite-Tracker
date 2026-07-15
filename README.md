# Elite Network Monitor

An interactive, browser-based **one-mode people network**. Two people are linked when they share an attribute you choose — a workplace (from career history), a school, or a region. Filter which people appear, toggle which link types are drawn, click a node to see the full profile. No backend: two files, works on GitHub Pages.

## Files

- `index.html` — the whole app (uses vis-network from a CDN).
- `data.json` — your data. **This is the only file you edit.** Ships with sample data; replace it with your 33 people.

## Data format

`data.json` has two arrays that mirror your Tab 1 and Tab 2.

```json
{
  "people": [
    { "id": 1, "name": "Full Name", "age": 54, "role": "Minister of Finance",
      "institution": "Ministry of Finance", "region": "Almaty", "school": "MGIMO",
      "zhuz": "Senior", "category": "Political elite" }
  ],
  "workExperience": [
    { "personId": 1, "title": "Minister of Finance", "institution": "Ministry of Finance",
      "startYear": 2021, "endYear": "Present" }
  ]
}
```

Rules:

- `people` = Tab 1, one object per person. `id` must be unique (1–33).
- `workExperience` = Tab 2, one object per role. `personId` matches a person's `id`.
- `category` drives node color. Use exactly one of: `Political elite`, `Business elite`, `Security/siloviki`, `Technocrat`, `Family member of power`.
- Unknown value? Use an empty string `""`. Do not write "N/A".
- **Institution names must be spelled identically** wherever they recur — that string match is exactly what creates the "shared workplace" links. "Almaty Akimat" and "Akimat of Almaty" will NOT connect.

## How the links work

- **Workplace (career history)** — links two people if any institution appears in *both* their `workExperience`. This is the elite-tie signal: same employer at some point, not just today.
- **School** — links people with the same `school`.
- **Region** — links people with the same `region`.

Turn each on/off with the checkboxes. Node size grows with number of links; node color = elite category.

## Run it locally

Because the app fetches `data.json`, double-clicking `index.html` may be blocked by the browser (file:// security). Two options:

1. Use the **Data → file picker** in the sidebar to load `data.json` manually. Simplest.
2. Or serve the folder: `python3 -m http.server` in this directory, then open `http://localhost:8000`.

## Host it on GitHub Pages (free, public URL)

1. Create a GitHub account and a new **public** repository, e.g. `elite-network`.
2. Upload `index.html` and `data.json` to the repo (drag-and-drop in the GitHub web UI → **Add file → Upload files → Commit**).
3. In the repo go to **Settings → Pages**.
4. Under **Build and deployment → Source**, choose **Deploy from a branch**. Set branch to `main` and folder to `/ (root)`. Save.
5. Wait ~1 minute. Your tool is live at `https://<your-username>.github.io/elite-network/`.

To update the data later, just edit `data.json` in the repo (pencil icon → commit). The live site refreshes automatically.

### Keep the data private?

GitHub Pages requires a public repo on the free plan, so the data is public. If the roster is sensitive, either keep it in a **private repo** and run locally (option 1/2 above), or host on a private-capable service (Netlify/Vercel with access control, or GitHub Pages on a paid org plan).

## Extending it

Easy next steps if you want them: weight links by *how many* institutions two people share, add a time slider (using `startYear`/`endYear` to show ties active in a given year), community detection to auto-color factions, or CSV export of the computed edges for Gephi. Ask and I'll add any of these.
