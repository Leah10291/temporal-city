"""SQLite storage. Every hours value is kept with its source, so nothing is overwritten."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time

DB_PATH = os.environ.get("TC_DB", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "temporal_city.db"))
_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS areas (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, kind TEXT, lat REAL, lon REAL, radius REAL,
  geojson TEXT, created REAL, discovered_at REAL, discovery_stats TEXT);
CREATE TABLE IF NOT EXISTS pois (
  id TEXT PRIMARY KEY, name TEXT, lat REAL, lon REAL, category TEXT, subtype TEXT, website TEXT,
  address TEXT, brand_wikidata TEXT, osm_opening_hours TEXT, tags TEXT, discovered_at REAL,
  retrieved_at REAL, final_weekly TEXT, final_label TEXT DEFAULT 'pending', final_source_id INTEGER,
  agreement REAL, n_sources INTEGER DEFAULT 0, perm_closed INTEGER DEFAULT 0, last_status TEXT);
CREATE TABLE IF NOT EXISTS poi_area (poi_id TEXT, area_id INTEGER, PRIMARY KEY (poi_id, area_id));
CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT, poi_id TEXT, source TEXT, method TEXT, url TEXT,
  evidence TEXT, weekly TEXT, confidence REAL, notes TEXT, created REAL);
CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, poi_id TEXT, step TEXT, url TEXT, status TEXT, created REAL);
CREATE TABLE IF NOT EXISTS audits (
  id INTEGER PRIMARY KEY AUTOINCREMENT, source_id INTEGER, poi_id TEXT, verdict TEXT,
  corrected TEXT, note TEXT, created REAL);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX IF NOT EXISTS ix_sources_poi ON sources(poi_id);
CREATE INDEX IF NOT EXISTS ix_attempts_poi ON attempts(poi_id);
CREATE INDEX IF NOT EXISTS ix_poi_area_area ON poi_area(area_id);
"""

DEFAULT_SETTINGS = {
    "use_google": "0", "google_api_key": "", "google_max_calls": "200",
    "use_web": "1", "use_search": "1", "use_wikidata": "1",
    "extraction": "hybrid",  # rules | llm | hybrid
    "cross_check": "1",       # keep collecting a 2nd source even when one is found (for verification)
    "llm_provider": "none", "llm_base_url": "", "llm_api_key": "", "llm_model": "",
    "crawl_delay": "1.5", "max_pages": "4",
    "search_engine": "auto",  # auto (DuckDuckGo → Bing) | duckduckgo | bing
    "proxy": "",              # e.g. http://127.0.0.1:7890 (Clash) — needed in mainland China
}


def connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


_con: sqlite3.Connection | None = None


def con() -> sqlite3.Connection:
    global _con
    if _con is None:
        _con = connect()
        _con.executescript(SCHEMA)
    return _con


def q(sql: str, args=()) -> list[dict]:
    with _lock:
        return [dict(r) for r in con().execute(sql, args).fetchall()]


def x(sql: str, args=()) -> int:
    with _lock:
        cur = con().execute(sql, args)
        con().commit()
        _maybe_checkpoint()
        return cur.lastrowid


# ------------------------------------------------------------------ keep the .db file complete
# The database runs in WAL mode: new rows first go to temporal_city.db-wal and only later into
# temporal_city.db. Anyone copying, zipping or committing just the .db file (the -wal file is in
# .gitignore) would lose recent work. So the WAL is folded back into the .db file a few seconds
# after writes, after every background job, and when the app closes.
_last_ckpt = 0.0


def checkpoint() -> None:
    global _last_ckpt
    with _lock:
        try:
            con().execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass
        _last_ckpt = time.time()


def _maybe_checkpoint() -> None:
    if time.time() - _last_ckpt > 10:
        checkpoint()


def summary() -> dict:
    """What is in this database file (shown at start-up and in the Atlas when it finds nothing)."""
    areas = q("SELECT a.id, a.name, COUNT(pa.poi_id) AS n FROM areas a LEFT JOIN poi_area pa ON pa.area_id=a.id GROUP BY a.id ORDER BY a.id")
    n = q("SELECT COUNT(*) AS n FROM pois")[0]["n"]
    return {"path": DB_PATH, "pois": n, "areas": areas}


import atexit  # noqa: E402
atexit.register(checkpoint)


def get_settings() -> dict:
    s = dict(DEFAULT_SETTINGS)
    for r in q("SELECT key, value FROM settings"):
        s[r["key"]] = r["value"]
    return s


def save_settings(new: dict):
    for k, v in new.items():
        if k in DEFAULT_SETTINGS:
            x("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
              (k, str(v)))


def add_source(poi_id, source, method, url, evidence, weekly, confidence, notes="") -> int:
    return x("INSERT INTO sources(poi_id,source,method,url,evidence,weekly,confidence,notes,created) "
             "VALUES(?,?,?,?,?,?,?,?,?)",
             (poi_id, source, method, url or "", evidence or "", json.dumps(weekly) if weekly else None,
              confidence, notes or "", time.time()))


def log_attempt(poi_id, step, url, status):
    x("INSERT INTO attempts(poi_id,step,url,status,created) VALUES(?,?,?,?,?)",
      (poi_id, step, url or "", status, time.time()))


def reset_all():
    with _lock:
        c = con()
        for t in ("areas", "pois", "poi_area", "sources", "attempts", "audits"):
            c.execute(f"DELETE FROM {t}")
        c.commit()
