"""Optional AI extraction. Turns messy page text into a structured weekly schedule.

Providers (choose in Settings):
  - "none"      : rule-based parser only (works offline, no AI)
  - "ollama"    : a local model served by Ollama (http://localhost:11434), free
  - "openai"    : any OpenAI-compatible endpoint (Gemini free tier, Groq, DeepSeek, OpenAI …)
  - "anthropic" : Claude API

Anti-hallucination guard: the model must quote the exact text it used; the quote
has to appear in the source snippet, otherwise the result is rejected.
"""
from __future__ import annotations

import json
import re

import requests

from . import net

from . import hours

PROMPT = """You extract opening hours for ONE specific place from web page text.

Place: {name}
Address hint: {address}
Category: {category}

Page title: {title}
Page text (excerpts):
<<<
{snippet}
>>>

Rules:
- Only use what the text states. Never guess. If the text does not give hours for this place, set "found": false.
- If the page lists several branches, use only the branch matching the address hint; if you cannot tell which branch, set "branch_match": "unclear".
- Times in 24h "HH:MM". Past midnight: end time may be smaller than start (e.g. "18:00"-"02:00"). Closed day = [].
- Ignore public-holiday-only rules.
- "evidence_quote": copy the exact sentence(s) from the text you relied on (verbatim).

Return ONLY JSON:
{{"found": true, "branch_match": "yes|no|unclear|single-location",
 "weekly": {{"mo": [["09:00","18:00"]], "tu": [], "we": [], "th": [], "fr": [], "sa": [], "su": []}},
 "evidence_quote": "...", "notes": "..."}}"""


def _call(settings: dict, prompt: str) -> str:
    p = settings.get("llm_provider", "none")
    model = settings.get("llm_model", "")
    if p == "ollama":
        base = (settings.get("llm_base_url") or "http://localhost:11434").rstrip("/")
        r = requests.post(f"{base}/api/generate", timeout=180,
                          json={"model": model or "qwen2.5:7b", "prompt": prompt, "stream": False, "format": "json",
                                "options": {"temperature": 0}})
        r.raise_for_status()
        return r.json().get("response", "")
    if p == "openai":
        base = (settings.get("llm_base_url") or "https://api.openai.com/v1").rstrip("/")
        r = net.session.post(f"{base}/chat/completions", timeout=120,
                          headers={"Authorization": f"Bearer {settings.get('llm_api_key', '')}"},
                          json={"model": model or "gpt-4o-mini", "temperature": 0,
                                "messages": [{"role": "user", "content": prompt}]})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    if p == "anthropic":
        r = net.session.post("https://api.anthropic.com/v1/messages", timeout=120,
                          headers={"x-api-key": settings.get("llm_api_key", ""), "anthropic-version": "2023-06-01"},
                          json={"model": model or "claude-haiku-5-5", "max_tokens": 800, "temperature": 0,
                                "messages": [{"role": "user", "content": prompt}]})
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json().get("content", []))
    raise RuntimeError("LLM provider not configured")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9:]", " ", (s or "").lower())).strip()


def quote_in_source(quote: str, source: str) -> bool:
    q, s = _norm(quote), _norm(source)
    if len(q) < 6:
        return False
    if q in s:
        return True
    # tolerate the model stitching several lines: every 4-word chunk must occur in the source
    words = q.split()
    chunks = [" ".join(words[i:i + 4]) for i in range(0, max(1, len(words) - 3), 4)]
    return all(c in s for c in chunks)


def extract(settings: dict, poi: dict, title: str, snippet: str) -> dict:
    """Return {"weekly", "confidence", "evidence", "notes", "status"}."""
    prompt = PROMPT.format(name=poi.get("name", ""), address=poi.get("address") or "unknown",
                           category=poi.get("category", ""), title=title, snippet=snippet[:3500])
    try:
        raw = _call(settings, prompt)
    except Exception as e:
        return {"status": f"llm error: {type(e).__name__}: {str(e)[:120]}"}
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return {"status": "llm returned no JSON"}
    try:
        data = json.loads(m.group(0))
    except Exception:
        return {"status": "llm returned invalid JSON"}
    if not data.get("found"):
        return {"status": "llm: no hours for this place"}
    if data.get("branch_match") == "no":
        return {"status": "llm: hours belong to another branch"}
    quote = str(data.get("evidence_quote") or "")
    if not quote_in_source(quote, snippet):
        return {"status": "rejected: quote not found in source (possible hallucination)"}
    weekly = hours.normalise(data.get("weekly") or {})
    if not weekly:
        return {"status": "llm: empty schedule"}
    conf = 0.65 if data.get("branch_match") in ("yes", "single-location") else 0.45
    if not hours.is_complete(weekly):
        conf -= 0.1
    return {"status": "ok", "weekly": weekly, "confidence": round(conf, 2), "evidence": quote[:600],
            "notes": f"branch_match={data.get('branch_match')}; {str(data.get('notes') or '')[:200]}"}
