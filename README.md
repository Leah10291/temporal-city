# Temporal City

**When is a mixed-use city actually open?**

Mixed-use planning records which land uses sit together, not when their amenities are available. Temporal City builds hour-by-hour opening data for every amenity in an area and compares that 24-hour availability with the area's land-use mix.

- **Website:** https://temporal-city-nus.github.io/temporal-city/
- **Full Collector (online server):** https://temporal-city.onrender.com/collector.html (free server; may take about a minute to wake up)

## Pages

| Page | What it shows |
|---|---|
| **Story** | The argument in one scroll: drag the clock and watch amenities in three Singapore catchments switch on and off. |
| **Collector** | Builds the dataset: find every amenity in an area, get its opening hours, check the evidence, export. |
| **Atlas** | Maps and comparisons: hourly heat, 3D and GFA layers, and six research questions answered from the data. |
| **Information** | Research question, method, data, limitations and references. |

## Data

- **Three case areas** (400 m around Bencoolen, Tanjong Pagar and Promenade MRT): Google Places sample, 595 places, 466 with opening hours.
- **Any other area:** amenities from OpenStreetMap; opening hours from OSM, Google Places (your own key) and business websites.
- **Land use and plot ratio:** URA Master Plan 2019 (case areas) and 2025 (other areas).

## How AI is used

AI turns opening hours written as free text on websites ("Mon–Fri 9am to 6pm; closed at weekends") into a structured 7 × 24 weekly schedule. It is used only where OSM, Google and simple rules cannot read the text. The model must quote the sentence it used; if the quote is not on the page, the result is rejected. Any model can be chosen in **00 Setup** (Gemini, Groq, DeepSeek, OpenAI, Claude, or Ollama locally).

Every result keeps its source, link and evidence, and gets a quality label: **verified** (two sources agree), **observed** (OSM), **retrieved** (one source), **conflict**, **estimated** or **missing**. Only the first three are analysed.

## Using the Collector

The Collector on the website runs in your browser and keeps your data and keys there. Steps: **00 Setup → 01 Area → 02 Discover → 03 Hours → 04 Review → 05 Explore → 06 Export**.

- With **00 Setup → Online server** ticked, business websites are read by the project's server on Render and your AI model; your key is sent with each request and not stored.
- You can also paste opening-hours text in **03 → Google check**, and the AI reads it.
- The full online version (link above) and the local app run the same Collector on a server.

## Run locally

```
py -m pip install -r requirements.txt
py app.py
```

Open http://127.0.0.1:8765. Data stays in `data/temporal_city.db` on your computer.

## Update the website

- **GitHub Pages:** after changing files in `static/`, run `py tools/build_pages.py` and upload the project (the site is served from `docs/`).
- **Render:** after uploading to GitHub, open the service on Render and choose **Manual Deploy → Deploy latest commit**.

## Limitations

- The AI can misread text, and its accuracy has not yet been measured on a large sample.
- Hours in images, PDFs or JavaScript-built pages cannot be read; web search sometimes finds the wrong pages (these are rejected).
- Small shops and hawkers are under-recorded; opening hours are not the same as actual use.
- Three Central Area catchments show an association, not a cause.
- The case-area sample comes from Google Places and is used for non-commercial research only.

The full list is on the Information page.

## Team

Bao Yihan, Li Jingyao, Lin Keyu, Yan Linhao · College of Design and Engineering, National University of Singapore.

Map data © OpenStreetMap contributors · Land use © URA · Places data © Google
