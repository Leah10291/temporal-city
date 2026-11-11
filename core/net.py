"""Polite HTTP: identifies itself, obeys robots.txt, rate-limits per domain."""
from __future__ import annotations

import threading
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests

USER_AGENT = "TemporalCityResearchBot/1.0 (academic research on opening hours; NUS AR5958A)"
BROWSER_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-SG,en;q=0.9",
}
MAX_BYTES = 2_500_000

_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
_last_hit: dict[str, float] = {}
_lock = threading.Lock()
session = requests.Session()
session.headers.update(BROWSER_HEADERS)


def configure(proxy: str = ""):
    """Apply a proxy (e.g. http://127.0.0.1:7890) to every request the app makes. Empty = system settings."""
    proxy = (proxy or "").strip()
    session.proxies.clear()
    if proxy:
        if not proxy.startswith(("http://", "https://", "socks5://", "socks5h://")):
            proxy = "http://" + proxy
        session.proxies.update({"http": proxy, "https": proxy})
    _robots.clear()


def _wait_turn(host: str, delay: float):
    with _lock:
        now = time.time()
        wait = _last_hit.get(host, 0) + delay - now
        _last_hit[host] = max(now, _last_hit.get(host, 0) + delay)
    if wait > 0:
        time.sleep(wait)


def robots_allowed(url: str) -> bool:
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = session.get(base + "/robots.txt", timeout=10)
            if r.status_code >= 400:
                rp = None  # no robots.txt → allowed
            else:
                rp.parse(r.text.splitlines())
        except Exception:
            rp = None
        _robots[base] = rp
    rp = _robots[base]
    return True if rp is None else rp.can_fetch(USER_AGENT, url)


def fetch(url: str, delay: float = 1.5, check_robots: bool = True) -> tuple[str | None, str]:
    """Return (html, status_note)."""
    try:
        if check_robots and not robots_allowed(url):
            return None, "blocked by robots.txt"
        _wait_turn(urlparse(url).netloc, delay)
        r = session.get(url, timeout=20, stream=True, allow_redirects=True)
        ctype = r.headers.get("content-type", "")
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}"
        if "html" not in ctype and "xml" not in ctype and ctype:
            return None, f"not html ({ctype.split(';')[0]})"
        body = b""
        for chunk in r.iter_content(65536):
            body += chunk
            if len(body) > MAX_BYTES:
                break
        r.encoding = r.encoding or "utf-8"
        return body.decode(r.encoding or "utf-8", errors="replace"), "ok"
    except Exception as e:
        return None, f"error: {type(e).__name__}"
