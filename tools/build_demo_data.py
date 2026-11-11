"""Data for the public (GitHub Pages) Collector: the real interface, read-only.

Builds a throw-away database from the Google Places sample of the three case areas (the same 595
places the Story and Atlas use), runs the normal reconcile step so every place gets its usual quality
label, then asks the real Flask app for every read-only response the Collector needs. The answers are
saved to docs/static/demo/data.json; docs/static/web-collector.js uses it for the three case areas.

    py tools/build_demo_data.py        (build_pages.py runs it automatically)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs")
EXPORTS = ["pois.csv", "pois.geojson", "hourly_matrix.csv", "availability_profiles.csv",
           "evidence_sources.csv", "crawl_attempts.csv", "audits.csv"]
PER_AREA = ["pois.csv", "pois.geojson"]


def sample() -> list[dict]:
    html = open(os.path.join(ROOT, "static", "atlas.html"), encoding="utf-8").read()
    i = html.index("const DATA=") + len("const DATA=")
    return json.JSONDecoder().raw_decode(html[i:])[0]


def weekly_from_days(days: list[str]) -> dict:
    keys = ["mo", "tu", "we", "th", "fr", "sa", "su"]
    out = {}
    for k, t in zip(keys, days or []):
        t = (t or "").strip()
        if t == "Closed":
            out[k] = []
        elif t[:1].isdigit():
            out[k] = [p.strip().split("-", 1) for p in t.split(",") if "-" in p]
    return out


def main():
    tmp = tempfile.mkdtemp(prefix="tc_demo_")
    os.environ["TC_DB"] = os.path.join(tmp, "demo.db")
    os.environ["TC_PUBLIC_DEMO"] = "1"
    sys.path.insert(0, ROOT)
    import app as appmod  # noqa: E402  (reads TC_DB / TC_PUBLIC_DEMO at import)
    from core import db, hours, pipeline  # noqa: E402

    now = time.time()
    ids = {}
    for c in appmod.CASE_STUDIES:
        ids[c["name"]] = db.x("INSERT INTO areas(name,kind,lat,lon,radius,created,discovered_at,discovery_stats) "
                              "VALUES(?,?,?,?,?,?,?,?)",
                              (c["name"], "circle", c["lat"], c["lon"], c["radius"], now, now,
                               json.dumps({"source": "Google Places sample"})))
    from collections import Counter
    smp = sample()
    for c in appmod.CASE_STUDIES:  # discovery summary shown in step 02, from the sample itself
        rows = [p for p in smp if p["d"] == c["name"]]
        db.x("UPDATE areas SET discovery_stats=? WHERE id=?",
             (json.dumps({"raw": len(rows), "non_functional": 0, "kept": len(rows), "with_osm_hours": 0,
                          "by_category": dict(Counter(p["c"] for p in rows)), "source": "Google Places sample"}), ids[c["name"]]))
    for p in smp:
        db.x("INSERT OR REPLACE INTO pois(id,name,lat,lon,category,subtype,tags,discovered_at,retrieved_at) "
             "VALUES(?,?,?,?,?,?,?,?,?)",
             (p["id"], p["n"], p["lat"], p["lng"], p["c"], p.get("type") or "", "{}", now, now))
        db.x("INSERT OR IGNORE INTO poi_area(poi_id,area_id) VALUES(?,?)", (p["id"], ids[p["d"]]))
        url = "https://www.google.com/maps/place/?q=place_id:" + p["id"]
        weekly = hours.normalise(weekly_from_days(p.get("days"))) if p.get("v") else {}
        if weekly:
            db.add_source(p["id"], "google", "places_api", url, "Google Places API · regularOpeningHours",
                          weekly, 0.85, "Google Places sample for the case areas")
        else:
            db.log_attempt(p["id"], "google", url, "no opening hours in Google Places")
        pipeline.reconcile(p["id"])
    db.checkpoint()

    c = appmod.app.test_client()
    get = lambda u: c.get(u).get_json()
    areas = get("/api/areas")
    pois = get("/api/pois")
    data = {
        "meta": get("/api/meta"),
        "settings": get("/api/settings"),
        "job": get("/api/job"),
        "areas": areas,
        "pois": pois,
        "poiAreas": {str(a["id"]): [r["id"] for r in get(f"/api/pois?area_id={a['id']}")] for a in areas},
        "details": {r["id"]: get("/api/pois/" + r["id"]) for r in pois},
        "coverage": {"all": get("/api/coverage"), **{str(a["id"]): get(f"/api/coverage?area_id={a['id']}") for a in areas}},
        "validation": get("/api/validation"),
        "auditSample": get("/api/audit_sample?per=8"),
    }
    # compact 7 x 24 states for availability / states / queue, computed in the browser like the server does
    data["mat"] = {}
    for pid, d in data["details"].items():
        m = d.get("matrix")
        data["mat"][pid] = "".join("." if v is None else str(v) for row in m for v in row) if m else ""
        d.pop("matrix", None)  # demo-api.js rebuilds it from mat
    os.makedirs(os.path.join(OUT, "static", "demo"), exist_ok=True)
    with open(os.path.join(OUT, "static", "demo", "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    size = os.path.getsize(os.path.join(OUT, "static", "demo", "data.json"))
    labels = {}
    for r in pois:
        labels[r["final_label"]] = labels.get(r["final_label"], 0) + 1
    print(f"demo data: {len(pois)} POIs in {len(areas)} areas, labels {labels}, {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
