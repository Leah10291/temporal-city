"""Exports: POI table, hourly matrix, availability profiles, all evidence, audits, GeoJSON."""
from __future__ import annotations

import csv
import io
import json

from . import analysis, db, hours


def _csv(rows: list[dict], fields: list[str]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return "﻿" + buf.getvalue()  # BOM so Excel opens UTF-8 correctly


def _poi_rows(area_id=None):
    if area_id:
        rows = db.q("SELECT p.* FROM pois p JOIN poi_area a ON a.poi_id=p.id WHERE a.area_id=? ORDER BY p.category, p.name", (area_id,))
    else:
        rows = db.q("SELECT * FROM pois ORDER BY category, name")
    areas = {}
    for r in db.q("SELECT pa.poi_id, ar.name FROM poi_area pa JOIN areas ar ON ar.id=pa.area_id"):
        areas.setdefault(r["poi_id"], []).append(r["name"])
    src = {s["id"]: s for s in db.q("SELECT id, source, method, url, confidence FROM sources")}
    out = []
    for r in rows:
        w = json.loads(r["final_weekly"]) if r["final_weekly"] else None
        s = src.get(r["final_source_id"]) or {}
        row = {**r, "areas": "; ".join(areas.get(r["id"], [])), "hours_text": hours.to_text(w),
               "final_source": f"{s.get('source', '')}/{s.get('method', '')}" if s else "",
               "source_url": s.get("url", ""), "confidence": s.get("confidence", "")}
        for d in hours.DAYS:
            row[d] = "" if not w or d not in w else (",".join(f"{a}-{b}" for a, b in w[d]) or "closed")
        out.append(row)
    return out


POI_FIELDS = ["id", "name", "category", "subtype", "lat", "lon", "address", "areas", "final_label", "final_source",
              "confidence", "agreement", "n_sources", "hours_text", *hours.DAYS, "source_url", "website",
              "osm_opening_hours", "perm_closed"]


def pois_csv(area_id=None) -> str:
    return _csv(_poi_rows(area_id), POI_FIELDS)


def hourly_csv(area_id=None) -> str:
    rows = []
    for r in _poi_rows(area_id):
        if not r["final_weekly"]:
            continue
        m = hours.to_matrix(json.loads(r["final_weekly"]))
        for di, d in enumerate(hours.DAYS):
            for h in range(24):
                if m[di][h] is not None:
                    rows.append({"poi_id": r["id"], "name": r["name"], "category": r["category"],
                                 "label": r["final_label"], "day": d, "hour": h, "open": m[di][h]})
    return _csv(rows, ["poi_id", "name", "category", "label", "day", "hour", "open"])


def profiles_csv(labels=None) -> str:
    rows = []
    for a in db.q("SELECT * FROM areas ORDER BY id"):
        for dt in ("weekday", "saturday", "sunday"):
            av = analysis.availability(a["id"], labels, dt)
            for c, v in av.items():
                for h in range(24):
                    rows.append({"area": a["name"], "category": c, "daytype": dt, "hour": h,
                                 "open_count": v["open"][h], "usable_records": v["usable"], "total_pois": v["total"],
                                 "relative_availability": v["share"][h], "record_coverage": v["coverage"]})
    return _csv(rows, ["area", "category", "daytype", "hour", "open_count", "usable_records", "total_pois",
                       "relative_availability", "record_coverage"])


def sources_csv() -> str:
    rows = db.q("SELECT s.*, p.name FROM sources s JOIN pois p ON p.id=s.poi_id ORDER BY s.poi_id, s.id")
    for r in rows:
        r["hours_text"] = hours.to_text(json.loads(r["weekly"])) if r["weekly"] else ""
    return _csv(rows, ["id", "poi_id", "name", "source", "method", "hours_text", "confidence", "url", "evidence", "notes"])


def attempts_csv() -> str:
    rows = db.q("SELECT t.*, p.name FROM attempts t JOIN pois p ON p.id=t.poi_id ORDER BY t.poi_id, t.id")
    return _csv(rows, ["poi_id", "name", "step", "url", "status"])


def audits_csv() -> str:
    rows = db.q("SELECT a.*, s.source, s.method, s.url, p.name FROM audits a JOIN sources s ON s.id=a.source_id "
                "JOIN pois p ON p.id=a.poi_id ORDER BY a.id")
    return _csv(rows, ["id", "poi_id", "name", "source", "method", "verdict", "corrected", "note", "url"])


def geojson(area_id=None) -> str:
    feats = []
    for r in _poi_rows(area_id):
        props = {k: r.get(k) for k in POI_FIELDS if k not in ("lat", "lon")}
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                      "properties": props})
    return json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False)
