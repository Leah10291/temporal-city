# Temporal City

**When is a mixed-use city actually open?**

Mixed-use planning records which land uses sit together, but not when their amenities are available. An area that looks mixed on the map can offer far less after dark. Temporal City adds the time dimension: it builds hour-by-hour opening data for every amenity in a study area and compares that 24-hour availability with the area's land-use composition.

**Live site:** https://temporal-city-nus.github.io/temporal-city/

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
| Opening hours in any other area | OSM tags, Google Places (with the user's own key), business websites | Collector |
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

**Collector steps:** 00 Setup (Google key, AI model, proxy, connection test) → 01 Area → 02 Discover → 03 Hours → 04 Review → 05 Explore → 06 Export (CSV, GeoJSON, or open the areas in the Atlas). In the Atlas, switch the data source to **Collector database** to analyse your own areas; up to eight can be compared.

**Exports:** `pois.csv` / `pois.geojson`, `hourly_matrix.csv`, `availability_profiles.csv`, `evidence_sources.csv`, `crawl_attempts.csv`, `audits.csv`.

---

## Publishing the site

`docs/` is the static build served by GitHub Pages (Settings → Pages → main, `/docs`). After editing anything in `static/`, rebuild it:

```
py tools/build_pages.py
```

On the public site the Collector page is a walkthrough with screenshots, because GitHub Pages cannot run the Python server. `render.yaml` and `Dockerfile` can deploy a read-only version with the Collector to Render.

---

## Limitations

In brief (full list on the Information page):

- **AI:** it can misread branches or past-midnight rules; the quote check proves the sentence exists, not that it was read correctly. Its accuracy at scale is not yet measured, and it cannot read hours shown in images, PDFs or JavaScript-built pages.
- **Data:** small operators and hawkers are under-recorded; opening hours describe scheduled availability, not actual use; holidays are not modelled.
- **Scope:** three Central Area catchments show an association, not a cause.
- **Google data:** the case-area sample comes from the Google Places API and is shown for non-commercial research only. Places data © Google.

---

## Repository structure

```
app.py                  Local server: pages, Collector API, background jobs
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
static/                 The four pages (local version)
docs/                   Static build for GitHub Pages
tools/                  Build scripts for the Atlas, land use and the public site
tests/                  Unit tests
data/                   Station list, simplified Master Plan 2025, local database
```

---

## Team

Bao Yihan, Li Jingyao, Lin Keyu, Yan Linhao. College of Design and Engineering, National University of Singapore.

Map data © OpenStreetMap contributors (ODbL). Land use from URA Master Plan 2019 and 2025. Places data © Google.
