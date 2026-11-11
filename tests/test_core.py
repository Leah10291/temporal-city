"""Run:  py -m pytest tests   (or: py tests/test_core.py)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import hours, llm
from core.discovery import classify


def T(w):
    return hours.to_text(w)


def test_osm_basic():
    assert T(hours.parse_osm("Mo-Fr 09:00-18:00; Sa 10:00-14:00; Su off")[0]) == "Mo-Fr 09:00-18:00; Sa 10:00-14:00; Su off"
    assert T(hours.parse_osm("24/7")[0]) == "24/7"
    assert T(hours.parse_osm("10:00-22:00")[0]) == "Mo-Su 10:00-22:00"


def test_osm_override_and_overnight():
    w, _ = hours.parse_osm("Mo-Su 10:00-22:00; Su off")
    assert w["su"] == [] and w["mo"] == [["10:00", "22:00"]]
    m = hours.to_matrix(hours.parse_osm("Fr-Sa 18:00-02:00; Su-Th off")[0])
    assert m[5][1] == 1 and m[6][1] == 1 and m[6][2] == 0  # Sat 1am (from Fri), Sun 1am (from Sat)


def test_hour_any_part_rule():  # one rule for Collector, Atlas and Story
    m = hours.to_matrix(hours.parse_osm("07:00-18:00")[0])
    assert m[0][7] == 1 and m[0][17] == 1 and m[0][18] == 0 and m[0][6] == 0
    m = hours.to_matrix(hours.parse_osm("11:30-21:30")[0])
    assert m[0][10] == 0 and m[0][11] == 1 and m[0][21] == 1 and m[0][22] == 0
    m = hours.to_matrix({"fr": [["18:00", "02:00"]]})   # past midnight spills into Saturday
    assert m[4][23] == 1 and m[5][0] == 1 and m[5][1] == 1 and m[5][2] is None


def test_atlas_sample_uses_same_rule():
    """The Atlas sample profiles (built by the dashboard) equal core.hours on their own hours text."""
    import json as _json, os as _os, re as _re
    from core import atlas_bridge
    html = open(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "static", "atlas.html"), encoding="utf-8").read()
    i = html.index("const DATA=") + len("const DATA=")
    data = _json.JSONDecoder().raw_decode(html[i:])[0]
    for p in data:
        if not p["v"]:
            continue
        wk = {}
        for d, txt in zip(hours.DAYS, p["days"]):
            if txt == "Unknown":
                continue
            wk[d] = [] if txt == "Closed" else [list(_re.match(r"(\d\d:\d\d)-(\d\d:\d\d)", x.strip()).groups()) for x in txt.split(";")]
        assert atlas_bridge.hourly_any(wk) == p["s"], p["n"]


def test_text_formats():
    cases = {
        "Opening Hours\nMon - Fri: 11am - 10pm\nSat & Sun: 10am - 10.30pm": "Mo-Fr 11:00-22:00; Sa-Su 10:00-22:30",
        "Open daily 1000hrs - 2200hrs": "Mo-Su 10:00-22:00",
        "Mon–Sat 12nn – 9pm | Sun: closed": "Mo-Sa 12:00-21:00; Su off",
        "Business Hours: 9-6pm daily": "Mo-Su 09:00-18:00",
        "Operating hours: 24 hours daily": "24/7",
        "Hours: Monday - Saturday 10:00 - 21:00, Sunday 10:00 - 18:00": "Mo-Sa 10:00-21:00; Su 10:00-18:00",
        "Weekdays 8am-8pm, Weekends closed": "Mo-Fr 08:00-20:00; Sa-Su off",
    }
    for txt, want in cases.items():
        assert T(hours.parse_text(txt)["weekly"]) == want, txt


def test_text_no_false_positive():
    assert hours.parse_text("Call 6123 4567. Set lunch $12.50")["weekly"] is None


def test_schema_and_google():
    spec = [{"dayOfWeek": ["Monday", "Tuesday"], "opens": "09:00", "closes": "17:00"},
            {"dayOfWeek": "https://schema.org/Saturday", "opens": "10:00:00", "closes": "14:00:00"}]
    assert T(hours.from_schema_spec(spec)) == "Mo-Tu 09:00-17:00; Sa 10:00-14:00"
    periods = [{"open": {"day": d, "hour": 8, "minute": 0}, "close": {"day": d, "hour": 20, "minute": 0}} for d in range(1, 6)]
    assert T(hours.from_google_periods(periods)) == "Mo-Fr 08:00-20:00; Sa-Su off"


def test_agreement():
    a = hours.parse_osm("Mo-Fr 09:00-18:00; Sa,Su off")[0]
    b = hours.parse_osm("Mo-Fr 09:00-17:00; Sa,Su off")[0]
    assert abs(hours.agreement(a, b) - (1 - 5 / 168)) < 1e-3


def test_classify():
    assert classify({"amenity": "cafe"})[0] == "Food & Beverage"
    assert classify({"amenity": "bench"})[0] is None
    assert classify({"amenity": "pharmacy", "healthcare": "pharmacy"})[0] == "Services"
    assert classify({"amenity": "library"})[0] == "Education"
    assert classify({"shop": "clothes"})[0] == "Retail"
    assert classify({"office": "company"})[0] is None


def test_llm_quote_guard():
    src = "Opening hours\nMon-Fri 8am - 6pm\nSat 9am-3pm"
    assert llm.quote_in_source("Mon-Fri 8am - 6pm", src)
    assert not llm.quote_in_source("Mon-Sun 7am - 11pm", src)


def test_atlas_analysis_matches_sample():
    """Rebuilding the Atlas COMPARE figures from the sample POIs must reproduce the shipped ones."""
    import json as _json
    import os as _os
    from core import atlas_bridge
    html = open(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "static", "atlas.html"), encoding="utf-8").read()

    def get(name):
        i = html.index("const " + name + "=") + len("const " + name + "=")
        return _json.JSONDecoder().raw_decode(html[i:])[0]
    sample, data = get("ANALYSIS"), get("DATA")
    rebuilt = atlas_bridge.build_analysis(data, sample, 0, 0)

    def same(a, b):
        if isinstance(a, dict):
            return all(same(a[k], b[k]) for k in a)
        if isinstance(a, list):
            return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
        if isinstance(a, float) or isinstance(b, float):
            return abs(a - b) < 1e-6
        return a == b
    assert same(sample["temporal"], rebuilt["temporal"])
    assert rebuilt["meta"]["in_scope_pois"] == sample["meta"]["in_scope_pois"]


def test_landuse_matches_sample_definitions():
    """Land-use entropy, GPR coverage and GFA computed here equal the GIS figures shipped for the sample."""
    import json as _json
    import os as _os
    from core import landuse
    html = open(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "static", "atlas.html"), encoding="utf-8").read()

    def get(name):
        i = html.index("const " + name + "=") + len("const " + name + "=")
        return _json.JSONDecoder().raw_decode(html[i:])[0]
    parcels, analysis = get("PARCEL_GEOJSON"), get("ANALYSIS")
    for d, ref in analysis["spatial"].items():
        mine = landuse.spatial_summary([f for f in parcels["features"] if f["properties"]["district"] == d], ref["catchment_area_m2"])
        for k in ("land_area_entropy", "six_class_area_m2", "numeric_gpr_coverage_pct", "partial_gfa_m2", "partial_gfa_entropy", "excluded_road_other_area_m2"):
            assert abs(mine[k] - ref[k]) <= max(0.5, abs(ref[k]) * 1e-3), (d, k, mine[k], ref[k])


def test_landuse_clip_covers_circle():
    """Clipping a square that contains the whole circle returns the circle; a parcel outside returns nothing."""
    from core import landuse
    clip = landuse.circle(400)
    big = [(-1000, -1000), (1000, -1000), (1000, 1000), (-1000, 1000)]
    assert abs(landuse.ring_area(landuse.clip_convex(big, clip)) - landuse.ring_area(clip)) < 1e-6
    far = [(2000, 2000), (2100, 2000), (2100, 2100)]
    assert landuse.clip_convex(far, clip) == []
    assert landuse.lu_class("Commercial & Residential") == "Mixed" and landuse.numeric_gpr("LND") is None and landuse.numeric_gpr("4.2") == 4.2


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f()
            print("ok ", k)
