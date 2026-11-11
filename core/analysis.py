"""Step 05 — temporal amenity availability, coverage and validation statistics."""
from __future__ import annotations

import json
import math
from collections import defaultdict

from . import db, hours
from .discovery import CATEGORIES

DAYTYPES = {"weekday": [0, 1, 2, 3, 4], "saturday": [5], "sunday": [6], "weekend": [5, 6],
            **{d: [i] for i, d in enumerate(hours.DAYS)}}
DEFAULT_LABELS = ["verified", "observed", "retrieved"]


def _pois(area_id=None):
    if area_id:
        rows = db.q("SELECT p.* FROM pois p JOIN poi_area a ON a.poi_id=p.id WHERE a.area_id=?", (area_id,))
    else:
        rows = db.q("SELECT * FROM pois")
    return [r for r in rows if not r["perm_closed"]]


def availability(area_id=None, labels=None, daytype="weekday") -> dict:
    """Per category and hour: absolute open count, usable records, total POIs, relative share.

    Weekday/weekend values are averages over the days in that group.
    Relative availability = open POIs ÷ POIs with usable records (proposal §2.3).
    Absolute availability = number of open POIs.
    """
    labels = labels or DEFAULT_LABELS
    days = DAYTYPES.get(daytype, DAYTYPES["weekday"])
    pois = _pois(area_id)
    cats = CATEGORIES + ["All"]
    total = {c: 0 for c in cats}
    usable = {c: 0 for c in cats}
    open_ = {c: [0.0] * 24 for c in cats}
    for p in pois:
        c = p["category"]
        total[c] += 1
        total["All"] += 1
        if p["final_label"] not in labels or not p["final_weekly"]:
            continue
        m = hours.to_matrix(json.loads(p["final_weekly"]))
        if any(m[d][0] is None for d in days):
            continue
        usable[c] += 1
        usable["All"] += 1
        for h in range(24):
            v = sum(m[d][h] for d in days) / len(days)
            open_[c][h] += v
            open_["All"][h] += v
    out = {}
    for c in cats:
        out[c] = {
            "total": total[c], "usable": usable[c],
            "coverage": round(usable[c] / total[c], 3) if total[c] else None,
            "open": [round(v, 2) for v in open_[c]],
            "share": [round(v / usable[c], 3) if usable[c] else None for v in open_[c]],
        }
    return out


def poi_states(area_id=None, labels=None, day="mo", hour=12) -> list[dict]:
    labels = labels or DEFAULT_LABELS
    di = hours.DAYS.index(day) if day in hours.DAYS else 0
    out = []
    for p in _pois(area_id):
        st = "nodata"
        if p["final_label"] in labels and p["final_weekly"]:
            v = hours.to_matrix(json.loads(p["final_weekly"]))[di][hour]
            st = "open" if v == 1 else "closed" if v == 0 else "nodata"
        out.append({"id": p["id"], "state": st})
    return out


def coverage(area_id=None) -> dict:
    labels = ["verified", "observed", "retrieved", "conflict", "estimated", "missing", "pending"]
    tab = {c: {l: 0 for l in labels} | {"total": 0} for c in CATEGORIES + ["All"]}
    for p in _pois(area_id):
        for c in (p["category"], "All"):
            tab[c][p["final_label"] or "pending"] += 1
            tab[c]["total"] += 1
    return tab


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None, None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(p, 3), round(max(0, c - h), 3), round(min(1, c + h), 3)


def validation() -> dict:
    # (1) manual audit accuracy by method
    rows = db.q("SELECT a.verdict, s.source, s.method FROM audits a JOIN sources s ON s.id=a.source_id")
    acc = defaultdict(lambda: {"correct": 0, "incorrect": 0, "unsure": 0})
    for r in rows:
        acc[f"{r['source']}/{r['method']}"][r["verdict"]] += 1
    accuracy = []
    for k, v in sorted(acc.items()):
        n = v["correct"] + v["incorrect"]
        p, lo, hi = wilson(v["correct"], n)
        accuracy.append({"method": k, **v, "n": n, "accuracy": p, "ci_low": lo, "ci_high": hi})
    # (2) cross-source agreement on POIs with ≥2 independent sources
    by_poi = defaultdict(list)
    for s in db.q("SELECT poi_id, source, method, url, weekly FROM sources WHERE weekly IS NOT NULL AND source NOT IN ('estimate','manual')"):
        by_poi[s["poi_id"]].append(s)
    from urllib.parse import urlparse
    pairs = defaultdict(list)
    for lst in by_poi.values():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                a, b = lst[i], lst[j]
                if a["source"] == b["source"] and urlparse(a["url"]).netloc == urlparse(b["url"]).netloc:
                    continue
                ag = hours.agreement(json.loads(a["weekly"]), json.loads(b["weekly"]))
                if ag is None:
                    continue
                key = " vs ".join(sorted([f"{a['source']}/{a['method']}", f"{b['source']}/{b['method']}"]))
                pairs[key].append(ag)
    agreement = [{"pair": k, "n": len(v), "mean": round(sum(v) / len(v), 3),
                  "share_ge_90": round(sum(1 for x in v if x >= 0.9) / len(v), 3)} for k, v in sorted(pairs.items())]
    return {"accuracy": accuracy, "agreement": agreement, "n_audits": len(rows), "backtest": estimation_backtest()}


def estimation_backtest(min_peers: int = 5) -> dict:
    """Leave-one-out test of the peer-majority estimator on POIs whose hours ARE known.

    Shows how wrong estimated hours would be — the evidence needed before (not) using them.
    """
    known = db.q("SELECT id, subtype, final_weekly FROM pois WHERE final_label IN ('verified','observed','retrieved') "
                 "AND final_weekly IS NOT NULL")
    mats = defaultdict(list)
    for k in known:
        w = json.loads(k["final_weekly"])
        if hours.is_complete(w):
            mats[k["subtype"]].append(hours.to_matrix(w))
    res, allv = [], []
    for sub, ms in mats.items():
        if len(ms) < min_peers + 1:
            continue
        scores = []
        for i, m in enumerate(ms):
            peers = ms[:i] + ms[i + 1:]
            same = sum(1 for d in range(7) for h in range(24)
                       if (1 if sum(p[d][h] for p in peers) * 2 > len(peers) else 0) == m[d][h])
            scores.append(same / 168)
        allv += scores
        res.append({"subtype": sub, "n": len(ms), "hour_accuracy": round(sum(scores) / len(scores), 3),
                    "exact_week_share": round(sum(1 for x in scores if x == 1) / len(scores), 3)})
    res.sort(key=lambda r: -r["n"])
    return {"by_subtype": res, "overall": round(sum(allv) / len(allv), 3) if allv else None, "n": len(allv)}
