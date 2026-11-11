"""Build data/mp2025_landuse.json.gz from URA's Master Plan 2025 land-use layer (GeoJSON, EPSG:4326).

    py tools/build_landuse.py path\\to\\MasterPlan2025LandUseLayer.geojson

Keeps only what the Atlas needs (land-use description, GPR, geometry rounded to ~0.1 m) so the
layer ships with the app (~15 MB instead of 190 MB). Re-run when URA publishes a new Master Plan.
"""
import gzip
import json
import os
import sys

src = sys.argv[1]
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mp2025_landuse.json.gz")
g = json.load(open(src, encoding="utf-8"))
desc, idx, feats = [], {}, []
for f in g["features"]:
    p, geom = f["properties"], f.get("geometry") or {}
    d = (p.get("LU_DESC") or "").strip().upper()
    if d not in idx:
        idx[d] = len(desc)
        desc.append(d)
    polys = [geom["coordinates"]] if geom.get("type") == "Polygon" else geom.get("coordinates", []) if geom.get("type") == "MultiPolygon" else []
    for poly in polys:
        rings = [[round(v, 6) for pt in ring for v in pt[:2]] for ring in poly if len(ring) >= 4]
        if not rings:
            continue
        xs, ys = rings[0][0::2], rings[0][1::2]
        feats.append([idx[d], p.get("GPR"), min(xs), min(ys), max(xs), max(ys), rings])
with gzip.open(out, "wt", encoding="utf-8", compresslevel=9) as fh:
    json.dump({"source": os.path.basename(src), "desc": desc, "f": feats}, fh, separators=(",", ":"))
print("wrote", out, len(feats), "polygons,", round(os.path.getsize(out) / 1e6, 1), "MB")
