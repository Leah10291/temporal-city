"""Step 02 — automatic POI discovery from OpenStreetMap (Overpass API, no key).

Nothing is imported from the user: the only input is a study area (circle or polygon).
POIs are classified into the six functional categories used in the proposal.
"""
from __future__ import annotations

import math
import time

import requests

from . import net

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

CATEGORIES = ["Food & Beverage", "Retail", "Services", "Education", "Community & Civic", "Culture & Recreation"]

# key=value → category. "*" = any value for that key. Order matters: first match wins.
_RULES: list[tuple[str, set[str] | str, str | None]] = [
    # ---- explicitly not functional amenities (removed, as in Figure 2.3)
    ("amenity", {"bench", "parking", "parking_space", "parking_entrance", "bicycle_parking", "motorcycle_parking",
                 "toilets", "waste_basket", "waste_disposal", "recycling", "drinking_water", "shelter", "atm",
                 "vending_machine", "telephone", "post_box", "fountain", "clock", "taxi", "bus_station",
                 "charging_station", "loading_dock", "smoking_area", "bicycle_rental", "grit_bin", "letter_box",
                 "parcel_locker", "photo_booth", "water_point", "hunting_stand", "lounger", "dog_toilet"}, None),
    ("tourism", {"hotel", "hostel", "guest_house", "apartment", "motel", "information", "artwork", "viewpoint",
                 "picnic_site", "camp_site"}, None),
    ("leisure", {"pitch", "playground", "garden", "park", "picnic_table", "outdoor_seating", "track", "common",
                 "dog_park", "swimming_area", "slipway", "marina", "nature_reserve", "firepit", "bandstand"}, None),
    # ---- Food & Beverage
    ("amenity", {"restaurant", "cafe", "fast_food", "bar", "pub", "food_court", "ice_cream", "biergarten",
                 "juice_bar", "canteen", "hawker_centre"}, "Food & Beverage"),
    ("shop", {"bakery", "pastry", "coffee", "tea", "bubble_tea", "confectionery", "beverages", "chocolate",
              "dessert"}, "Food & Beverage"),
    # ---- Education (library included, per proposal Figure 2.3)
    ("amenity", {"school", "university", "college", "kindergarten", "library", "language_school", "music_school",
                 "driving_school", "training", "prep_school", "dancing_school", "research_institute"}, "Education"),
    # ---- Community & Civic
    ("amenity", {"community_centre", "social_centre", "social_facility", "townhall", "police", "fire_station",
                 "courthouse", "place_of_worship", "clinic", "doctors", "dentist", "hospital", "childcare",
                 "public_building", "nursing_home", "embassy"}, "Community & Civic"),
    ("office", {"government", "diplomatic"}, "Community & Civic"),
    # ---- Services
    ("amenity", {"bank", "bureau_de_change", "money_transfer", "pharmacy", "post_office", "veterinary",
                 "car_wash", "car_rental", "fuel", "internet_cafe", "studio", "payment_centre"}, "Services"),
    ("shop", {"hairdresser", "beauty", "massage", "laundry", "dry_cleaning", "travel_agency", "tailor", "copyshop",
              "funeral_directors", "money_lender", "pawnbroker", "repair", "mobile_phone_repair", "tattoo",
              "nail_salon", "cosmetics_services", "photo", "optician_services", "shoe_repair", "locksmith"}, "Services"),
    ("craft", "*", "Services"),
    ("healthcare", "*", "Community & Civic"),
    # ---- Culture & Recreation
    ("amenity", {"cinema", "theatre", "arts_centre", "nightclub", "casino", "karaoke_box", "events_venue",
                 "conference_centre", "exhibition_centre", "planetarium", "music_venue", "gambling"},
     "Culture & Recreation"),
    ("tourism", {"museum", "gallery", "attraction", "zoo", "aquarium", "theme_park"}, "Culture & Recreation"),
    ("leisure", {"fitness_centre", "sports_centre", "swimming_pool", "bowling_alley", "amusement_arcade",
                 "escape_game", "dance", "sauna", "fitness_station", "ice_rink", "golf_course",
                 "trampoline_park", "adult_gaming_centre", "hackerspace", "water_park", "miniature_golf"},
     "Culture & Recreation"),
    # ---- Retail (any remaining shop)
    ("amenity", {"marketplace"}, "Retail"),
    ("shop", "*", "Retail"),
]


def classify(tags: dict) -> tuple[str | None, str]:
    """Return (category or None if non-functional, subtype like 'amenity=cafe')."""
    for key, values, cat in _RULES:
        v = tags.get(key)
        if v is None:
            continue
        if values == "*" or v in values:
            return cat, f"{key}={v}"
    for key in ("amenity", "shop", "tourism", "leisure", "office", "craft", "healthcare"):
        if key in tags:
            return None, f"{key}={tags[key]}"
    return None, ""


def haversine(lat1, lon1, lat2, lon2) -> float:
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def point_in_polygon(lat, lon, rings) -> bool:
    """rings: list of [[lon, lat], ...] (GeoJSON order). Even-odd rule across all rings."""
    inside = False
    for ring in rings:
        n = len(ring)
        j = n - 1
        for i in range(n):
            xi, yi = ring[i][0], ring[i][1]
            xj, yj = ring[j][0], ring[j][1]
            if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi:
                inside = not inside
            j = i
    return inside


def polygon_rings(geojson: dict) -> list[list[list[float]]]:
    """Flatten (Multi)Polygon / Feature / FeatureCollection into a list of outer+inner rings."""
    g = geojson
    if g.get("type") == "FeatureCollection":
        rings = []
        for f in g.get("features", []):
            rings += polygon_rings(f)
        return rings
    if g.get("type") == "Feature":
        return polygon_rings(g.get("geometry") or {})
    if g.get("type") == "Polygon":
        return [list(r) for r in g["coordinates"]]
    if g.get("type") == "MultiPolygon":
        return [list(r) for poly in g["coordinates"] for r in poly]
    return []


def _area_filter(area: dict) -> str:
    if area["kind"] == "circle":
        return f"(around:{float(area['radius']):.0f},{float(area['lat']):.6f},{float(area['lon']):.6f})"
    rings = polygon_rings(area["geojson"])
    outer = max(rings, key=len)  # Overpass poly filter takes one ring; exact test is applied afterwards
    pts = " ".join(f"{lat:.6f} {lon:.6f}" for lon, lat in outer[:-1] if True)
    return f'(poly:"{pts}")'


def build_query(area: dict) -> str:
    f = _area_filter(area)
    parts = "".join(f"nwr[\"{k}\"]{f};" for k in ("amenity", "shop", "tourism", "leisure", "craft", "healthcare", "office"))
    return f"[out:json][timeout:120];({parts});out center tags;"


def run_overpass(query: str, log=print, stop=lambda: False) -> dict:
    errors = []
    for url in OVERPASS_ENDPOINTS:
        if stop():
            raise RuntimeError("stopped")
        host = url.split('/')[2]
        t0 = time.time()
        log(f"  Overpass → {host} …")
        try:
            # connect timeout 12 s, read timeout 75 s (a 400 m catchment normally answers in < 15 s)
            r = net.session.post(url, data={"data": query}, timeout=(12, 75))
            if r.status_code == 200:
                log(f"  Overpass OK ({host}, {time.time() - t0:.0f} s)")
                return r.json()
            msg = f"HTTP {r.status_code}" + (" (server busy)" if r.status_code in (429, 504) else "")
        except requests.exceptions.ConnectTimeout:
            msg = "cannot connect (timeout) — network/firewall blocks this server?"
        except requests.exceptions.ReadTimeout:
            msg = "server too slow (no answer in 75 s)"
        except requests.exceptions.ConnectionError as e:
            msg = "connection error: " + str(e)[:120]
        except Exception as e:
            msg = f"{type(e).__name__}: {str(e)[:120]}"
        log(f"  ✗ {host}: {msg}")
        errors.append(f"{host}: {msg}")
    raise RuntimeError("All Overpass servers failed. Open Settings → Test connections. If you are in mainland China, "
                       "set a proxy (e.g. http://127.0.0.1:7890) in Settings. Details: " + " | ".join(errors))


def elements_to_pois(data: dict, area: dict) -> tuple[list[dict], dict]:
    """Convert Overpass JSON into POI dicts that fall inside the area. Returns (pois, stats)."""
    pois, stats = [], {"raw": 0, "outside": 0, "non_functional": 0, "kept": 0}
    rings = polygon_rings(area["geojson"]) if area["kind"] == "polygon" else None
    for el in data.get("elements", []):
        stats["raw"] += 1
        tags = el.get("tags") or {}
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue
        if area["kind"] == "circle":
            if haversine(lat, lon, float(area["lat"]), float(area["lon"])) > float(area["radius"]):
                stats["outside"] += 1
                continue
        elif not point_in_polygon(lat, lon, rings):
            stats["outside"] += 1
            continue
        cat, sub = classify(tags)
        if cat is None:
            stats["non_functional"] += 1
            continue
        stats["kept"] += 1
        addr = " ".join(x for x in [tags.get("addr:housenumber"), tags.get("addr:street"),
                                     tags.get("addr:unit"), tags.get("addr:postcode")] if x)
        pois.append({
            "id": f"{el['type']}/{el['id']}",
            "name": tags.get("name:en") or tags.get("name") or "",
            "lat": lat, "lon": lon,
            "category": cat, "subtype": sub,
            "website": tags.get("website") or tags.get("contact:website") or tags.get("url") or "",
            "address": addr,
            "brand_wikidata": tags.get("brand:wikidata") or "",
            "osm_opening_hours": tags.get("opening_hours") or "",
            "tags": tags,
        })
    return pois, stats
