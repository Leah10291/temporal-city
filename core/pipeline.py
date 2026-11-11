"""Orchestration: discovery → retrieval → reconciliation (quality labels) → estimation."""
from __future__ import annotations

import json
import random
import time
from collections import Counter
from urllib.parse import urlparse

from . import crawler, db, discovery, google_places, hours, llm

# Which records count as what (see README "Quality labels")
PRIORITY = {("manual", "manual"): 9, ("google", "places_api"): 5, ("osm", "osm_tag"): 4,
            ("web", "jsonld"): 4, ("web", "llm"): 3, ("web", "rules"): 2, ("estimate", "peer_majority"): 0}
AGREE = 0.9  # two independent sources agreeing on ≥90 % of the week's hours → "verified"


# ============================================================ discovery
def discover_area(area: dict, log=print, stop=lambda: False) -> dict:
    log(f"Discovering POIs in “{area['name']}” …")
    data = discovery.run_overpass(discovery.build_query(area), log=log, stop=stop)
    pois, stats = discovery.elements_to_pois(data, area)
    now = time.time()
    new = 0
    for p in pois:
        exists = db.q("SELECT id FROM pois WHERE id=?", (p["id"],))
        if not exists:
            new += 1
            db.x("INSERT INTO pois(id,name,lat,lon,category,subtype,website,address,brand_wikidata,"
                 "osm_opening_hours,tags,discovered_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                 (p["id"], p["name"], p["lat"], p["lon"], p["category"], p["subtype"], p["website"], p["address"],
                  p["brand_wikidata"], p["osm_opening_hours"], json.dumps(p["tags"]), now))
        else:  # refresh OSM attributes, keep retrieved data
            db.x("UPDATE pois SET name=?,lat=?,lon=?,category=?,subtype=?,website=?,address=?,brand_wikidata=?,"
                 "osm_opening_hours=?,tags=? WHERE id=?",
                 (p["name"], p["lat"], p["lon"], p["category"], p["subtype"], p["website"], p["address"],
                  p["brand_wikidata"], p["osm_opening_hours"], json.dumps(p["tags"]), p["id"]))
        db.x("INSERT OR IGNORE INTO poi_area(poi_id, area_id) VALUES(?,?)", (p["id"], area["id"]))
        _ingest_osm(p["id"], p["osm_opening_hours"])
        reconcile(p["id"])
    stats["new"] = new
    stats["by_category"] = dict(Counter(p["category"] for p in pois))
    stats["with_osm_hours"] = sum(1 for p in pois if p["osm_opening_hours"])
    db.x("UPDATE areas SET discovered_at=?, discovery_stats=? WHERE id=?", (now, json.dumps(stats), area["id"]))
    log(f"  {stats['raw']} raw OSM objects → {stats['kept']} functional POIs "
        f"({stats['non_functional']} non-functional removed, {stats['outside']} outside area); "
        f"{stats['with_osm_hours']} carry OSM opening_hours")
    return stats


def _ingest_osm(pid: str, value: str):
    """Store the OSM opening_hours tag as an 'observed' source (once per distinct value)."""
    if not value:
        return
    prev = db.q("SELECT evidence FROM sources WHERE poi_id=? AND source='osm'", (pid,))
    if any(r["evidence"] == value for r in prev):
        return
    db.x("DELETE FROM sources WHERE poi_id=? AND source='osm'", (pid,))  # tag changed in OSM → replace
    weekly, warn = hours.parse_osm(value)
    if weekly:
        db.add_source(pid, "osm", "osm_tag", f"https://www.openstreetmap.org/{pid}", value, weekly,
                      0.8 if not warn else 0.65, "; ".join(warn))
    else:
        db.log_attempt(pid, "osm", "", "unparseable opening_hours: " + value[:120])


# ============================================================ retrieval
class Budget:
    def __init__(self, google_max: int):
        self.google_left = google_max


def _has_hours(poi_id: str) -> bool:
    return bool(db.q("SELECT 1 FROM sources WHERE poi_id=? AND weekly IS NOT NULL AND source!='estimate' LIMIT 1",
                     (poi_id,)))


def _sources_of(poi_id):
    return db.q("SELECT source, method FROM sources WHERE poi_id=?", (poi_id,))


def retrieve_poi(poi: dict, s: dict, budget: Budget, log=print, stop=lambda: False) -> str:
    pid = poi["id"]
    poi = dict(poi)
    poi["tags"] = json.loads(poi.get("tags") or "{}")
    have = {(r["source"], r["method"]) for r in _sources_of(pid)}
    cross = s.get("cross_check") == "1"

    # 1 — OSM tag (observed)
    _ingest_osm(pid, poi.get("osm_opening_hours"))

    if not poi.get("name"):
        db.log_attempt(pid, "web", "", "skipped: POI has no name")
        return "no name"

    # 2 — Google Places (optional, key, call cap)
    if (s.get("use_google") == "1" and s.get("google_api_key") and ("google", "places_api") not in have
            and (cross or not _has_hours(pid))):
        if budget.google_left <= 0:
            db.log_attempt(pid, "google", "", "skipped: call cap reached")
        else:
            budget.google_left -= 1
            g = google_places.lookup(poi, s["google_api_key"])
            db.log_attempt(pid, "google", g.get("url", ""), g["status"])
            if g.get("permanently_closed"):
                db.x("UPDATE pois SET perm_closed=1 WHERE id=?", (pid,))
            if g["status"] == "ok":
                db.add_source(pid, "google", "places_api", g["url"], g["evidence"], g["weekly"], g["confidence"],
                              f"matched “{g['place_name']}” at {g['distance']} m")

    # 3 — Web pages
    if s.get("use_web") == "1" and not any(src == "web" for src, _ in have) and (cross or not _has_hours(pid)):
        if stop():
            return "stopped"
        _retrieve_web(poi, s, log)
    return "done"


def _candidate_urls(poi: dict, s: dict, log) -> list[tuple[str, str]]:
    cands: list[tuple[str, str]] = []
    if poi.get("website"):
        u = poi["website"] if poi["website"].startswith("http") else "https://" + poi["website"]
        cands.append((u, "osm_website"))
    if s.get("use_search") == "1":
        q = crawler.search_query(poi)
        found, eng = crawler.search(q, s.get("search_engine", "auto"), max_results=4, log=log)
        db.log_attempt(poi["id"], "search", q, f"{len(found)} results ({eng})")
        cands += [(u, "search") for u in found]
    if s.get("use_wikidata") == "1" and poi.get("brand_wikidata"):
        u = crawler.wikidata_website(poi["brand_wikidata"])
        if u:
            cands.append((u, "brand_wikidata"))
    seen, out = set(), []
    for u, how in cands:
        key = u.rstrip("/")
        if key not in seen and not crawler._skip(u):
            seen.add(key)
            out.append((u, how))
    return out


def _retrieve_web(poi: dict, s: dict, log):
    pid = poi["id"]
    max_pages = int(s.get("max_pages") or 4)
    delay = float(s.get("crawl_delay") or 1.5)
    mode = s.get("extraction", "hybrid")
    llm_on = s.get("llm_provider", "none") != "none"
    queue = _candidate_urls(poi, s, log)
    visited = 0
    while queue and visited < max_pages:
        url, how = queue.pop(0)
        visited += 1
        html, note = crawler.net.fetch(url, delay=delay)
        if html is None:
            db.log_attempt(pid, "fetch", url, note)
            continue
        page = crawler.parse_page(html, url)
        full = page["title"] + "\n" + page["text"]
        match = 1.0 if how in ("osm_website", "osm_website_link") else crawler.name_match(full, poi)
        addr_ok = crawler.address_hint(full, poi)
        if match < 0.5 and how not in ("brand_wikidata", "brand_link"):
            db.log_attempt(pid, "fetch", url, f"page does not mention the place (name match {match})")
            continue
        found = False
        # (a) structured schema.org data
        if page["structured"]:
            best = max(page["structured"], key=lambda st: (crawler.name_match(st[1] + " " + st[2], poi)
                                                            + (2 if crawler.address_hint(st[2], poi) else 0)))
            weekly, sname, saddr = best
            multi = len(page["structured"]) > 1
            conf = 0.85 * (0.6 + 0.4 * match) + (0.05 if addr_ok else 0) - (0.15 if multi and not crawler.address_hint(saddr, poi) else 0)
            db.add_source(pid, "web", "jsonld", url, f"schema.org openingHours: {hours.to_text(weekly)} ({sname} {saddr})"[:600],
                          weekly, round(min(conf, 0.95), 2), f"found via {how}; name match {match}")
            db.log_attempt(pid, "extract", url, "schema.org hours found")
            found = True
        # (b) text → rules and/or LLM
        if not found:
            snippet = crawler.hours_snippets(page["text"], poi)
            if snippet:
                rule = hours.parse_text(snippet) if mode in ("rules", "hybrid") else {"weekly": None, "confidence": 0}
                adj = (0.6 + 0.4 * match) + (0.1 if addr_ok else 0)
                if rule["weekly"]:
                    db.add_source(pid, "web", "rules", url, rule["evidence"], rule["weekly"],
                                  round(min(rule["confidence"] * adj, 0.9), 2),
                                  f"found via {how}; name match {match}; " + "; ".join(rule["notes"]))
                    found = True
                if llm_on and (mode == "llm" or (mode == "hybrid" and (not rule["weekly"] or rule["confidence"] < 0.6
                                                                     or s.get("cross_check") == "1"))):
                    res = llm.extract(s, poi, page["title"], snippet)
                    db.log_attempt(pid, "llm", url, res["status"])
                    if res["status"] == "ok":
                        db.add_source(pid, "web", "llm", url, res["evidence"], res["weekly"],
                                      round(min(res["confidence"] * adj, 0.9), 2), f"found via {how}; {res['notes']}")
                        found = True
                if not found:
                    db.log_attempt(pid, "extract", url, "hours keywords present but no schedule extracted")
            else:
                db.log_attempt(pid, "extract", url, "no opening-hours text on page")
        if found:
            return
        # (c) follow likely sub-pages (contact / outlets / hours) on the same site
        link_how = "osm_website_link" if how == "osm_website" else ("brand_link" if how == "brand_wikidata" else "site_link")
        for l in page["links"][:3]:
            if all(l.rstrip("/") != u.rstrip("/") for u, _ in queue):
                queue.insert(0, (l, link_how)) if how == "osm_website" else queue.append((l, link_how))


# ============================================================ reconciliation
def _independent(a: dict, b: dict) -> bool:
    if a["source"] != b["source"]:
        return True
    return urlparse(a["url"]).netloc != urlparse(b["url"]).netloc


def reconcile(pid: str):
    srcs = db.q("SELECT * FROM sources WHERE poi_id=? AND weekly IS NOT NULL", (pid,))
    audits = {a["source_id"]: a for a in db.q("SELECT * FROM audits WHERE poi_id=? ORDER BY created", (pid,))}
    for r in srcs:
        r["w"] = json.loads(r["weekly"])
        r["prio"] = PRIORITY.get((r["source"], r["method"]), 1) + r["confidence"]
        r["audit"] = audits.get(r["id"], {}).get("verdict")
    real = [r for r in srcs if r["source"] != "estimate" and r["audit"] != "incorrect"]
    est = [r for r in srcs if r["source"] == "estimate"]
    label, final, agree = "missing", None, None

    manual = [r for r in real if r["source"] == "manual"]
    confirmed = [r for r in real if r["audit"] == "correct"]
    if manual:
        final, label = max(manual, key=lambda r: r["created"]), "verified"
    elif confirmed:
        final, label = max(confirmed, key=lambda r: r["prio"]), "verified"
    elif real:
        best_pair, best_ag = None, -1.0
        for i in range(len(real)):
            for j in range(i + 1, len(real)):
                if not _independent(real[i], real[j]):
                    continue
                ag = hours.agreement(real[i]["w"], real[j]["w"])
                if ag is not None and ag > best_ag:
                    best_ag, best_pair = ag, (real[i], real[j])
        if best_pair and best_ag >= AGREE:
            final, label, agree = max(best_pair, key=lambda r: r["prio"]), "verified", best_ag
        elif best_pair:
            final, label, agree = max(real, key=lambda r: r["prio"]), "conflict", best_ag
        else:
            final = max(real, key=lambda r: r["prio"])
            label = "observed" if final["source"] == "osm" else "retrieved"
    elif est:
        final, label = est[-1], "estimated"
    else:
        tried = db.q("SELECT retrieved_at FROM pois WHERE id=?", (pid,))
        tried_now = db.q("SELECT 1 FROM attempts WHERE poi_id=? AND step!='osm' LIMIT 1", (pid,))
        if not (tried and tried[0]["retrieved_at"]) and not tried_now:
            label = "pending"
    n_real = len(real)
    db.x("UPDATE pois SET final_weekly=?, final_label=?, final_source_id=?, agreement=?, n_sources=? WHERE id=?",
         (json.dumps(final["w"]) if final else None, label, final["id"] if final else None, agree, n_real, pid))
    return label


def reconcile_all():
    for r in db.q("SELECT id FROM pois"):
        reconcile(r["id"])


# ============================================================ estimation
def estimate_missing(min_peers: int = 5, log=print) -> int:
    """Level-3 gap filling: hour-by-hour majority vote of comparable POIs (same OSM subtype).

    Estimated records are labelled 'estimated' and EXCLUDED from analysis by default, because
    a model trained on them could learn the estimation rule instead of real urban patterns.
    """
    db.x("DELETE FROM sources WHERE source='estimate'")
    pool = db.q("SELECT id, subtype, final_weekly FROM pois WHERE final_label IN ('verified','observed','retrieved') "
                "AND final_weekly IS NOT NULL")
    by_sub: dict[str, list] = {}
    for p in pool:
        w = json.loads(p["final_weekly"])
        if hours.is_complete(w):
            by_sub.setdefault(p["subtype"], []).append(hours.to_matrix(w))
    made = 0
    for p in db.q("SELECT id, subtype FROM pois WHERE final_label IN ('missing','pending')"):
        peers = by_sub.get(p["subtype"], [])
        if len(peers) < min_peers:
            continue
        mat = [[1 if sum(m[d][h] for m in peers) * 2 > len(peers) else 0 for h in range(24)] for d in range(7)]
        weekly = matrix_to_weekly(mat)
        db.add_source(p["id"], "estimate", "peer_majority", "", f"majority of {len(peers)} {p['subtype']} POIs",
                      weekly, 0.2, f"n_peers={len(peers)}")
        reconcile(p["id"])
        made += 1
    log(f"Estimated {made} POIs (subtypes with ≥{min_peers} known peers).")
    return made


def matrix_to_weekly(mat) -> dict:
    out = {}
    for di, d in enumerate(hours.DAYS):
        ivs, h = [], 0
        while h < 24:
            if mat[di][h]:
                s = h
                while h < 24 and mat[di][h]:
                    h += 1
                ivs.append([f"{s:02d}:00", "24:00" if h == 24 else f"{h:02d}:00"])
            else:
                h += 1
        out[d] = ivs
    return out


# ============================================================ audit sampling
def audit_sample(per_method: int = 10, seed: int | None = None) -> list[dict]:
    """Stratified random sample of not-yet-audited records: up to N per (source, method)."""
    rnd = random.Random(seed)
    rows = db.q("SELECT s.*, p.name, p.category, p.address, p.lat, p.lon FROM sources s JOIN pois p ON p.id=s.poi_id "
                "WHERE s.weekly IS NOT NULL AND s.source!='manual' AND s.id NOT IN (SELECT source_id FROM audits)")
    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(f"{r['source']}/{r['method']}", []).append(r)
    out = []
    for k, g in sorted(groups.items()):
        rnd.shuffle(g)
        for r in g[:per_method]:
            r["stratum"] = k
            r["weekly_text"] = hours.to_text(json.loads(r["weekly"]))
            out.append(r)
    return out
