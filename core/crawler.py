"""Step 03 — find web sources for a POI and pull opening-hours evidence out of them.

Website discovery order:
  1. website / contact:website tag already in OSM
  2. web search (DuckDuckGo HTML endpoint, no key) for "<name> <street> Singapore opening hours"
  3. brand official website from Wikidata (brand:wikidata) — chain homepage, low priority

For every page: structured data first (schema.org JSON-LD / microdata — machine readable,
high confidence), then the visible text around hours keywords (for the rule parser / LLM).
"""
from __future__ import annotations

import json
import re
import time
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from bs4 import BeautifulSoup

from . import hours, net

SKIP_DOMAINS = (
    "google.", "facebook.com", "instagram.com", "tiktok.com", "twitter.com", "x.com", "youtube.com",
    "tripadvisor.", "yelp.", "linkedin.com", "wikipedia.org", "pinterest.", "duckduckgo.com", "bing.com",
    "openstreetmap.org", "waze.com", "grab.com", "foodpanda.", "deliveroo.", "apple.com/maps",
)
FOLLOW_LINK = re.compile(r"contact|location|outlet|store|branch|visit|hours|find-us|findus|about|our-shop", re.I)
_search_blocked_until = 0.0


def _skip(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(d in host or d in url for d in SKIP_DOMAINS)


# ------------------------------------------------------------------ search
def search_duckduckgo(query: str, max_results: int = 5, log=print) -> list[str]:
    global _search_blocked_until
    if time.time() < _search_blocked_until:
        return []
    net._wait_turn("html.duckduckgo.com", 4.0)
    try:
        r = net.session.post("https://html.duckduckgo.com/html/", data={"q": query, "kl": "sg-en"}, timeout=(8, 20))
    except Exception as e:
        log(f"  DuckDuckGo unreachable ({type(e).__name__}); pausing it for 10 min, using Bing")
        _search_blocked_until = time.time() + 600
        return []
    if r.status_code != 200 or "anomaly" in r.text[:5000].lower() or "result__a" not in r.text:
        if r.status_code != 200 or "anomaly" in r.text[:5000].lower():
            _search_blocked_until = time.time() + 300
            log("  search engine is rate-limiting; pausing web search for 5 minutes")
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    urls = []
    for a in soup.select("a.result__a"):
        href = a.get("href", "")
        if "uddg=" in href:
            href = unquote(parse_qs(urlparse(href).query).get("uddg", [""])[0])
        if href.startswith("http") and not _skip(href) and href not in urls:
            urls.append(href)
        if len(urls) >= max_results:
            break
    return urls


def _bing_target(href: str) -> str:
    """Bing wraps results as bing.com/ck/a?...&u=a1<base64url>; unwrap them."""
    import base64
    if "bing.com/ck/a" in href:
        u = parse_qs(urlparse(href).query).get("u", [""])[0]
        if u.startswith("a1"):
            b = u[2:]
            try:
                return base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)).decode("utf-8", "replace")
            except Exception:
                return ""
    return href


def search_bing(query: str, max_results: int = 5, log=print) -> list[str]:
    """Bing HTML results (works from mainland China via cn.bing.com)."""
    global _search_blocked_until
    out = []
    for host in ("www.bing.com", "cn.bing.com"):
        net._wait_turn(host, 3.0)
        try:
            r = net.session.get(f"https://{host}/search", params={"q": query, "setlang": "en", "cc": "SG", "count": 10},
                                timeout=(10, 20))
        except Exception as e:
            log(f"  Bing ({host}) error: {type(e).__name__}")
            continue
        if r.status_code != 200:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("li.b_algo h2 a"):
            href = _bing_target(a.get("href", ""))
            if href.startswith("http") and not _skip(href) and href not in out:
                out.append(href)
            if len(out) >= max_results:
                break
        if out:
            break
    return out


def search(query: str, engine: str = "auto", max_results: int = 5, log=print) -> tuple[list[str], str]:
    if engine in ("auto", "duckduckgo"):
        res = search_duckduckgo(query, max_results, log)
        if res or engine == "duckduckgo":
            return res, "duckduckgo"
    return search_bing(query, max_results, log), "bing"


def wikidata_website(qid: str) -> str | None:
    if not re.fullmatch(r"Q\d+", qid or ""):
        return None
    try:
        r = net.session.get("https://www.wikidata.org/wiki/Special:EntityData/%s.json" % qid, timeout=15)
        claims = r.json()["entities"][qid]["claims"].get("P856", [])
        return claims[0]["mainsnak"]["datavalue"]["value"] if claims else None
    except Exception:
        return None


def search_query(poi: dict) -> str:
    street = (poi.get("tags") or {}).get("addr:street", "")
    return f"\"{poi['name']}\" {street} Singapore opening hours".replace("  ", " ")


# ------------------------------------------------------------ page parsing
def _walk_jsonld(obj):
    if isinstance(obj, list):
        for o in obj:
            yield from _walk_jsonld(o)
    elif isinstance(obj, dict):
        yield obj
        for k in ("@graph", "mainEntity", "location", "department", "subOrganization", "containsPlace"):
            if k in obj:
                yield from _walk_jsonld(obj[k])


def parse_page(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    structured = []  # list of (weekly, name, address_text)
    for tag in soup.find_all("script", type=lambda t: t and "ld+json" in t):
        try:
            data = json.loads(tag.string or tag.get_text() or "")
        except Exception:
            continue
        for node in _walk_jsonld(data):
            weekly = None
            if node.get("openingHoursSpecification"):
                weekly = hours.from_schema_spec(node["openingHoursSpecification"])
            elif node.get("openingHours"):
                oh = node["openingHours"]
                weekly, _ = hours.parse_osm("; ".join(oh) if isinstance(oh, list) else str(oh))
            if weekly:
                addr = node.get("address")
                addr = " ".join(str(v) for v in addr.values()) if isinstance(addr, dict) else str(addr or "")
                structured.append((weekly, str(node.get("name") or ""), addr))
    for el in soup.select('[itemprop="openingHours"]'):
        v = el.get("content") or el.get_text(" ")
        weekly, _ = hours.parse_osm(v)
        if weekly:
            structured.append((weekly, "", ""))
    title = (soup.title.get_text(" ").strip() if soup.title else "")[:200]
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        if urlparse(href).netloc == urlparse(url).netloc and FOLLOW_LINK.search(href + " " + a.get_text(" ")):
            if href.split("#")[0] != url and href not in links:
                links.append(href.split("#")[0])
    for t in soup(["script", "style", "noscript", "svg", "iframe"]):
        t.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return {"structured": structured, "text": text, "title": title, "links": links[:6]}


def _tokens(s: str) -> list[str]:
    stop = {"the", "and", "of", "singapore", "sg", "pte", "ltd", "restaurant", "cafe", "bar", "shop", "store", "&", "@"}
    return [t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(t) > 1 and t not in stop]


def name_match(text: str, poi: dict) -> float:
    toks = _tokens(poi.get("name", ""))
    if not toks:
        return 0.0
    low = text.lower()
    return round(sum(1 for t in toks if t in low) / len(toks), 2)


def address_hint(text: str, poi: dict) -> bool:
    tags = poi.get("tags") or {}
    pc = tags.get("addr:postcode")
    if pc and pc in text:
        return True
    street = tags.get("addr:street", "")
    hn = tags.get("addr:housenumber", "")
    return bool(street and hn and f"{hn} {street}".lower() in text.lower())


def hours_snippets(text: str, poi: dict, max_chars: int = 2500) -> str:
    """Lines around hours keywords; windows that also mention the branch/address are put first."""
    lines = text.split("\n")
    hits = []
    for i, ln in enumerate(lines):
        if hours.HOURS_KEYWORDS.search(ln) and (re.search(r"\d", ln) or re.search(r"hours|open|closed", ln, re.I)):
            lo, hi = max(0, i - 2), min(len(lines), i + 6)
            window = "\n".join(lines[lo:hi])
            score = 1 + (2 if address_hint(window, poi) else 0) + name_match(window, poi)
            hits.append((score, lo, window))
    hits.sort(key=lambda h: (-h[0], h[1]))
    out, used = [], 0
    for _, _, w in hits:
        if w in out:
            continue
        if used + len(w) > max_chars:
            break
        out.append(w)
        used += len(w)
    return "\n---\n".join(out)
