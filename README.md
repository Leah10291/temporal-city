# Temporal City

**When is a mixed-use city actually open?**

Mixed-use planning records which land uses sit together, but not when their amenities are available. An area that looks mixed on the map can offer far less after dark. Temporal City adds the time dimension: it builds hour-by-hour opening data for every amenity in a study area and compares that 24-hour availability with the area's land-use composition.

## Three ways to use it

| Version | Address | What works |
|---|---|---|
| **Public site** (GitHub Pages) | https://temporal-city-nus.github.io/temporal-city/ | All four pages. Its **Collector** links open the full online version below. A browser version (`collector.html`) keeps data and keys in your browser: any area via OpenStreetMap, Google Places with your own key, the three case areas from the project's sample, and websites + AI through the online server (00 Setup → *Online server*), or AI on text you paste. |
| **Full online Collector** (Render) | https://temporal-city.onrender.com/collector.html | The complete app, as in the local version: business websites, the AI reader, the Atlas on your own areas. Free server: it sleeps when idle and takes about a minute to wake. |
| **Local app** | `py app.py` → http://127.0.0.1:8765 | Everything, with your data and keys kept on your computer. |

The site has four pages:

| Page | What it shows |
|---|---|
| **Story** | The argument in one scroll: drag the clock and watch amenities in three Singapore catchments switch on and off. |
| **Collector** | The tool that builds the dataset: find every amenity in an area, retrieve its opening hours, check the evidence, export. |
| **Atlas** | Interactive maps and comparisons: hourly heat and 3D views, a GFA layer, and six research questions with findings computed from the data. |
| **Information** | Research question, project logic, data, method, limitations and references. |

All pages share a day/night switch (Auto follows the hour shown on the page).

---

## Study areas and data

| Data | Source | Used for |
|---|---|---|
| Amenities and opening hours, three case areas | Google Places API (595 places, 466 with opening hours) | Story and the Atlas sample |
| Amenities in any other area | OpenStreetMap (Overpass API) | Collector |
| Opening hours in any other area | OSM tags, Google Places (with the user's own key), business websites (full online / local versions) | Collector |
| Land use and gross plot ratio | URA Master Plan 2019 (case areas), Master Plan 2025 (other areas) | Land-use mix, GFA |
| Station locations | LTA station exits | Study-area catchments |

The case areas are 400 m catchments around **Bencoolen**, **Tanjong Pagar** and **Promenade** MRT stations in Singapore's Central Area. The Collector works for any MRT/LRT catchment, a point on the map or a GeoJSON polygon.

---

## How AI is used

AI is used for one task: **turning opening hours written as free text into structured data.**

Many places publish their hours only as sentences on a website ("Mon–Fri 9am to 6pm; closed at weekends", "Daily except PH, dinner till late"). Rules can read common formats but not the many ways people write them. The Collector tries sources in order and uses AI only where nothing else can read the text:

1. **OpenStreetMap** `opening_hours` tag
2. **Google Places API**, if the user adds a key
3. **Business websites**, found from OSM or by web search (DuckDuckGo, then Bing):
   - schema.org structured data first
   - then a rule-based parser
   - then the **AI model**, which receives the hours passage with the place's name and address and returns a 7-day, 24-hour schedule as JSON

Safeguards:

- The model must quote the sentence it relied on. The quote is checked against the page; if it is not there, the result is rejected.
- It must pick the branch that matches the address, or report that it cannot tell.
- It runs at temperature 0. AI results rank below Google Places and OSM and above rule parsing.
- Every value keeps its source, link, evidence text and a quality label (below).
- The model is interchangeable: Ollama (local, free), any OpenAI-compatible API (Gemini, Groq, DeepSeek, OpenAI) or Anthropic Claude. Without a model, only structured data and rules are used.

Where the AI runs: in the full online version and the local app the server reads business websites itself. The browser version on GitHub Pages cannot open other websites, so with *00 Setup → Online server* on it asks the Render server to search and read each place's website (`/api/web_lookup`), sending the visitor's AI key with that request only; the server returns the schedules with their evidence and stores nothing. The browser version can also run the AI directly on text the researcher pastes (03 → Google check). Every path uses the same prompt and quote check.

A future step, not yet built, would use AI to predict 24-hour availability from land-use mix across many catchments. Three areas are too few to train or test such a model.

---

## Quality labels

| Label | Meaning | Analysed |
|---|---|---|
| `verified` | Two independent sources agree on ≥ 90% of the 168 weekly hours, or a researcher confirmed it | yes |
| `observed` | OSM tag only | yes |
| `retrieved` | One web or Google source | yes |
| `conflict` | Sources disagree; needs review | no |
| `estimated` | Inferred from similar places | no |
| `missing` | Nothing found | no |

Places without usable hours are left out of the denominator, never counted as closed.

---

## Measures

- **Hourly state:** a place counts as open in hour *h* if it is open for any part of that hour; past-midnight hours carry into the next day.
- **Relative availability(h)** = open places at *h* ÷ places with usable hours. **Absolute availability(h)** = number of open places at *h*.
- Reported for weekdays (Monday–Friday average), Saturday and Sunday, by area and by six amenity categories.
- **Land-use mix:** normalised Shannon entropy over six planning classes (0 = one class, 1 = an even mix).
- **GFA** = clipped parcel area × numeric gross plot ratio; GFA-weighted availability weights each parcel's open share by its GFA.

---

## Run it locally

The Story, Atlas and Information pages are static. The Collector needs a small Python server.

```
py -m pip install -r requirements.txt
py app.py
```

Then open http://127.0.0.1:8765 (or double-click `start.bat` on Windows). Data is stored in `data/temporal_city.db`. API keys are entered in the Collector's Setup step and stay on your computer.

**Collector steps:** 00 Setup (Google key, AI model, proxy, connection test) → 01 Area → 02 Discover → 03 Hours (automatic retrieval, then Google check by hand) → 04 Review (records, validate accuracy) → 05 Explore → 06 Export (CSV, GeoJSON, or open the areas in the Atlas).

**Atlas data source:** two cards at the top right. **Google Places sample** is the case-study data for the three study areas and the basis of the project's findings; **Collector database** analyses new areas you collected yourself, up to eight at once (local app or full online version only).

**Exports:** `pois.csv` / `pois.geojson`, `hourly_matrix.csv`, `availability_profiles.csv`, `evidence_sources.csv`, `crawl_attempts.csv`, `audits.csv`.

---

## Publishing

### Public site (GitHub Pages)

`docs/` is the static build served by GitHub Pages (Settings → Pages → main, `/docs`). After editing anything in `static/`, rebuild it and upload `docs/` with the changed files:

```
py tools/build_pages.py
```

GitHub Pages cannot run the Python server. The site's Collector links therefore open the full version on Render, and `collector.html` is a browser version of the same Collector (`static/web-collector.js`, a port of the Python rules and the AI reader). Its data and keys stay in the visitor's browser. Each build gives scripts a new version number, so browsers load the new files.

### Full online Collector (Render)

`render.yaml` and `Dockerfile` deploy the Python app to Render's free plan as a Blueprint from this public repository. `TC_PUBLIC_DEMO=0` runs the full Collector; set it to `1` for a read-only copy. The same server answers `/api/web_lookup` for the browser version; `TC_WEB_ORIGINS` lists the sites allowed to call it (default: the GitHub Pages site).

- Render does not redeploy automatically from this repository: after uploading changes to GitHub, open the service on Render and choose **Manual Deploy → Deploy latest commit**.
- The free instance sleeps after about 15 minutes without visitors; the first request then takes about a minute.
- All visitors share one server: the areas and data are visible to every visitor and are lost when the server restarts. An API key entered in 00 Setup is shown only as its last four characters, but every visitor's runs use it until it is removed or the server restarts. Use a free-tier key (for example Gemini) and remove it after use. Ollama needs a model on your own computer, so online use a cloud model (Gemini, Groq, DeepSeek, OpenAI or Claude).

---

## Limitations

In brief (full table on the Information page, section 06):

**A · The AI approach**
- **Misreading:** the model can pick the wrong branch or miss past-midnight and holiday rules; the quote check proves the sentence exists, not that it was read correctly.
- **Accuracy not yet measured:** the case-area sample relies mostly on Google, so the AI path is untested at scale, and its confidence is a fixed score.
- **What it can read:** hours in images, PDF menus or JavaScript pages are missed; third-party pages can be outdated.
- **Future model not built:** three catchments cannot train or test a predictive model.

**B · Data, method and scope**
- **Coverage and accuracy:** small operators and hawkers are under-recorded; no independent audit yet.
- **Scheduled, not actual use:** holidays and temporary closures are not modelled; open does not mean busy.
- **Land use and GFA:** main planned use only; GFA from numeric plot ratios; MP2019 for case areas, MP2025 for new areas.
- **Google data terms:** the case-area sample is shown for non-commercial research only. Places data © Google.
- **Scope:** three Central Area catchments show an association, not a cause.

---

## Repository structure

```
app.py                  Server for the local app and Render: pages, Collector API, background jobs
Dockerfile, render.yaml  Render deployment
core/discovery.py       OpenStreetMap queries and the six amenity categories
core/crawler.py         Web search, page fetching, schema.org parsing, text extraction
core/llm.py             AI extraction and the quote check
core/google_places.py   Optional Google Places lookups
core/hours.py           Opening-hours parsing and the 7 × 24 matrix
core/pipeline.py        Source merging, quality labels, estimates, audit sampling
core/analysis.py        Availability, coverage and validation statistics
core/landuse.py         Land-use mix and GFA from the URA Master Plan
core/atlas_bridge.py    Feeds Collector data into the Atlas
core/export.py          CSV / GeoJSON export
static/                 The four pages (local and Render version); web-collector.js runs the Collector in the browser
docs/                   Static build for GitHub Pages
tools/                  Build scripts for the Atlas, land use and the public site
tests/                  Unit tests
data/                   Station list, simplified Master Plan 2025, local database
```

---

## Team

Bao Yihan, Li Jingyao, Lin Keyu, Yan Linhao. College of Design and Engineering, National University of Singapore.

Map data © OpenStreetMap contributors (ODbL). Land use from URA Master Plan 2019 and 2025. Places data © Google.
