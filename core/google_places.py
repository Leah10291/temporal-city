"""Optional source: Google Places API (New) Text Search — needs the user's own API key.

Google bills per request after the monthly free usage; the app enforces a hard
per-run call cap set in Settings. Results are matched to the OSM POI by distance and
name similarity, and the match quality is stored with the record.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

import requests

from . import hours, net
from .discovery import haversine

URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ("places.id,places.displayName,places.formattedAddress,places.location,"
          "places.regularOpeningHours,places.businessStatus,places.googleMapsUri")


def _sim(a: str, b: str) -> float:
    norm = lambda s: re.sub(r"[^a-z0-9 ]", "", (s or "").lower())
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def lookup(poi: dict, api_key: str, radius: float = 120.0) -> dict:
    """Return {"status", "weekly", "url", "evidence", "confidence", "place_name", "distance"}."""
    body = {
        "textQuery": f"{poi['name']} Singapore",
        "locationBias": {"circle": {"center": {"latitude": poi["lat"], "longitude": poi["lon"]}, "radius": radius}},
        "maxResultCount": 5,
        "languageCode": "en",
    }
    try:
        r = net.session.post(URL, json=body, timeout=20,
                          headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": FIELDS})
    except Exception as e:
        return {"status": f"error: {type(e).__name__}"}
    if r.status_code != 200:
        msg = ""
        try:
            msg = r.json().get("error", {}).get("message", "")[:160]
        except Exception:
            pass
        return {"status": f"HTTP {r.status_code} {msg}"}
    best, best_score = None, 0.0
    for p in r.json().get("places", []):
        loc = p.get("location") or {}
        d = haversine(poi["lat"], poi["lon"], loc.get("latitude", 0), loc.get("longitude", 0))
        s = _sim(poi["name"], (p.get("displayName") or {}).get("text", ""))
        score = s * (1.0 if d <= 60 else 0.8 if d <= 150 else 0.3)
        if score > best_score:
            best, best_score, best_d = p, score, d
    if not best or best_score < 0.45:
        return {"status": "no confident match"}
    if best.get("businessStatus") == "CLOSED_PERMANENTLY":
        return {"status": "permanently closed", "place_name": best["displayName"]["text"],
                "url": best.get("googleMapsUri", ""), "permanently_closed": True}
    roh = best.get("regularOpeningHours") or {}
    weekly = hours.from_google_periods(roh.get("periods"))
    if not weekly:
        return {"status": "matched but no hours", "place_name": best["displayName"]["text"]}
    return {
        "status": "ok",
        "weekly": weekly,
        "url": best.get("googleMapsUri", ""),
        "evidence": " | ".join(roh.get("weekdayDescriptions") or [])[:600],
        "confidence": round(min(0.9, 0.55 + 0.35 * best_score), 2),
        "place_name": best["displayName"]["text"],
        "distance": round(best_d, 1),
    }
