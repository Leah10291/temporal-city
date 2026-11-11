"""Land use, GPR and GFA for any study area, from URA Master Plan 2025 (data/mp2025_landuse.json.gz).

The Atlas compares land-use mix (entropy over six classes) and floor-area intensity (GFA = clipped
parcel area x numeric GPR) with amenity opening hours. The three case studies in the Google Places
sample were prepared in GIS from the Master Plan 2019 amendment; this module does the same for any
Collector study area, without GIS software: parcels are clipped to the area's catchment circle and
measured here. Definitions follow the sample (see ANALYSIS.spatial; checked in tests).
"""
from __future__ import annotations

import gzip
import io
import json
import math
import os
import re
from pathlib import Path

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MP_PATH = os.path.join(HERE, "data", "mp2025_landuse.json.gz")
MP_PARTS = [MP_PATH + ".part1", MP_PATH + ".part2"]
CLASSES = ["Residential", "Mixed", "Commercial", "Hotel", "Civic_Edu", "Open_Space"]

# Master Plan land-use description -> analysis class. The first 14 follow the group's GIS mapping of the
# three case studies; the rest (absent from the Central Area) are this project's choice — edit here.
LU_CLASS = {
    "RESIDENTIAL": "Residential",
    "COMMERCIAL & RESIDENTIAL": "Mixed", "RESIDENTIAL WITH COMMERCIAL AT 1ST STOREY": "Mixed", "WHITE": "Mixed",
    "RESIDENTIAL / INSTITUTION": "Mixed", "COMMERCIAL / INSTITUTION": "Mixed",
    "BUSINESS 1 - WHITE": "Mixed", "BUSINESS 2 - WHITE": "Mixed", "BUSINESS PARK - WHITE": "Mixed",
    "COMMERCIAL": "Commercial", "BUSINESS 1": "Commercial", "BUSINESS 2": "Commercial", "BUSINESS PARK": "Commercial",
    "HOTEL": "Hotel",
    "CIVIC & COMMUNITY INSTITUTION": "Civic_Edu", "EDUCATIONAL INSTITUTION": "Civic_Edu", "PLACE OF WORSHIP": "Civic_Edu",
    "HEALTH & MEDICAL CARE": "Civic_Edu",
    "OPEN SPACE": "Open_Space", "PARK": "Open_Space", "SPORTS & RECREATION": "Open_Space", "BEACH AREA": "Open_Space",
    "RESERVE SITE": "Other", "SPECIAL USE": "Other", "AGRICULTURE": "Other", "CEMETERY": "Other",
    "ROAD": "EXCLUDE", "UTILITY": "EXCLUDE", "WATERBODY": "EXCLUDE", "TRANSPORT FACILITIES": "EXCLUDE",
    "MASS RAPID TRANSIT": "EXCLUDE", "LIGHT RAPID TRANSIT": "EXCLUDE", "PORT / AIRPORT": "EXCLUDE",
}


def lu_class(desc: str | None) -> str:
    return LU_CLASS.get((desc or "").strip().upper(), "Other")


def numeric_gpr(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) if v > 0 else None
    return float(v) if re.fullmatch(r"\s*\d+(\.\d+)?\s*", str(v)) and float(v) > 0 else None


# ------------------------------------------------------------------ geometry (no GIS libraries needed)
def _xy(lat0: float, lon0: float):
    kx = 111_320 * math.cos(math.radians(lat0))
    return (lambda lon, lat: ((lon - lon0) * kx, (lat - lat0) * 111_320),
            lambda x, y: (lon0 + x / kx, lat0 + y / 111_320))


def ring_area(pts) -> float:
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i - 1]
        x2, y2 = pts[i]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def circle(r: float, n: int = 64):
    return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def clip_convex(subject, clip):
    """Sutherland–Hodgman: subject polygon (any shape) clipped by a convex, counter-clockwise polygon."""
    out = list(subject)
    for i in range(len(clip)):
        if not out:
            break
        ax, ay = clip[i - 1]
        bx, by = clip[i]
        inside = lambda p: (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax) >= 0  # noqa: E731

        def cross(p, q):
            dx, dy = q[0] - p[0], q[1] - p[1]
            ex, ey = bx - ax, by - ay
            den = dx * ey - dy * ex
            if den == 0:
                return q
            t = ((ax - p[0]) * ey - (ay - p[1]) * ex) / den
            return (p[0] + t * dx, p[1] + t * dy)
        inp, out = out, []
        for j in range(len(inp)):
            cur, prev = inp[j], inp[j - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(cross(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cross(prev, cur))
    return out


# ------------------------------------------------------------------ the Master Plan layer
_MP: dict | None = None


def available() -> bool:
    return os.path.exists(MP_PATH) or all(os.path.exists(path) for path in MP_PARTS)


def _load() -> dict:
    """Compact layer: {"desc": [...], "f": [[desc_i, gpr, minlon, minlat, maxlon, maxlat, [ring, ...]], ...]}
    with rings as flat [lon, lat, lon, lat, ...] lists (outer ring first, then holes) — one entry per polygon."""
    global _MP
    if _MP is None:
        source = MP_PATH if os.path.exists(MP_PATH) else io.BytesIO(
            b"".join(Path(path).read_bytes() for path in MP_PARTS)
        )
        with gzip.open(source, "rt", encoding="utf-8") as fh:
            mp = json.load(fh)
        grid: dict = {}
        for i, f in enumerate(mp["f"]):
            for gx in range(int(f[2] * 100), int(f[4] * 100) + 1):
                for gy in range(int(f[3] * 100), int(f[5] * 100) + 1):
                    grid.setdefault((gx, gy), []).append(i)
        mp["grid"] = grid
        _MP = mp
    return _MP


def parcels_for(name: str, lat: float, lon: float, r: float) -> tuple[list[dict], float]:
    """Master Plan parcels clipped to the circle (lat, lon, r metres): GeoJSON features in the Atlas
    PARCEL_GEOJSON format, and the catchment area in m²."""
    mp = _load()
    to_xy, to_ll = _xy(lat, lon)
    clip = circle(r)
    dlat, dlon = r / 111_320, r / (111_320 * math.cos(math.radians(lat)))
    cand = set()
    for gx in range(int((lon - dlon) * 100), int((lon + dlon) * 100) + 1):
        for gy in range(int((lat - dlat) * 100), int((lat + dlat) * 100) + 1):
            cand.update(mp["grid"].get((gx, gy), ()))
    feats = []
    for i in sorted(cand):
        desc_i, gpr_raw, x0, y0, x1, y1, rings = mp["f"][i]
        if x1 < lon - dlon or x0 > lon + dlon or y1 < lat - dlat or y0 > lat + dlat:
            continue
        clipped = []
        area = 0.0
        for k, flat in enumerate(rings):
            pts = [to_xy(flat[j], flat[j + 1]) for j in range(0, len(flat), 2)]
            c = clip_convex(pts, clip)
            if len(c) < 3:
                if k == 0:
                    break
                continue
            a = ring_area(c)
            area += a if k == 0 else -a
            clipped.append([[round(v, 7) for v in to_ll(x, y)] for x, y in c] + [[round(v, 7) for v in to_ll(*c[0])]])
        if not clipped or area < 0.5:
            continue
        desc = mp["desc"][desc_i]
        gpr = numeric_gpr(gpr_raw)
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": clipped},
                      "properties": {"id": f"{name}|mp{i}", "parcel_id": i, "district": name, "land_use": lu_class(desc),
                                     "land_use_desc": desc, "gpr_raw": gpr_raw, "clip_area_m2": round(area, 2), "gpr": gpr,
                                     "gfa_m2": round(area * gpr, 1) if gpr else None}})
    return feats, ring_area(clip)


def _entropy(values: list[float]) -> float | None:
    t = sum(values)
    if t <= 0:
        return None
    return -sum(v / t * math.log(v / t) for v in values if v > 0) / math.log(len(CLASSES))


def spatial_summary(feats: list[dict], catchment_m2: float) -> dict:
    """Same fields and definitions as ANALYSIS.spatial in the Atlas."""
    by = {c: 0.0 for c in CLASSES}
    gpr_area = {c: 0.0 for c in CLASSES}
    gfa = {c: 0.0 for c in CLASSES}
    other = excluded = 0.0
    for f in feats:
        p = f["properties"]
        c, a = p["land_use"], p["clip_area_m2"]
        if c == "EXCLUDE":
            excluded += a
        if c in by:
            by[c] += a
            if p["gpr"]:
                gpr_area[c] += a
                gfa[c] += a * p["gpr"]
        elif c == "Other":
            other += a
    six = sum(by.values())
    num = sum(gpr_area.values())
    return {
        "catchment_area_m2": catchment_m2, "six_class_area_m2": six,
        "six_class_coverage_pct": six / catchment_m2 * 100 if catchment_m2 else None,
        "land_area_entropy": _entropy(list(by.values())),
        "land_area_by_class_m2": {c: v for c, v in by.items() if v > 0},
        "land_area_by_class_pct": {c: v / six * 100 for c, v in by.items() if v > 0} if six else {},
        "other_unclassified_area_m2": other,
        "excluded_road_other_area_m2": excluded,
        "numeric_gpr_area_m2": num, "numeric_gpr_coverage_pct": num / six * 100 if six else None,
        "partial_gfa_m2": sum(gfa.values()), "partial_gfa_entropy": _entropy(list(gfa.values())),
        "partial_gfa_by_class_m2": {c: v for c, v in gfa.items() if v > 0},
        "numeric_gpr_coverage_by_class_pct": {c: gpr_area[c] / by[c] * 100 for c in CLASSES if by[c] > 0},
        "source": "URA Master Plan 2025",
    }
