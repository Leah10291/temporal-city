"""Opening-hours representation, parsing and comparison.

Weekly schedule format used everywhere in this project:
    {"mo": [["09:00", "18:00"]], "tu": [...], ..., "su": []}
    - an empty list means closed that day
    - a missing key means "unknown for that day"
    - an end time earlier than (or equal to) the start means the interval runs past
      midnight (e.g. ["18:00", "02:00"]); "24:00" is allowed as an end time.

Hourly state: a POI is counted as OPEN in hour h of a day if it is open for any
part of [h:00, h+1:00). So 07:00-18:00 is open from the 07 slot to the 17 slot and
closed at 18; 11:30-22:00 is open in the 11 slot. The Story page and the Atlas use
the same rule. (Proposal Table 2.3 used the instant h:00 instead; the group chose
"any part of the hour" so that a place opening at 11:30 counts in the 11:00 hour.)
"""
from __future__ import annotations

import re

DAYS = ["mo", "tu", "we", "th", "fr", "sa", "su"]
DAY_LABEL = {"mo": "Mon", "tu": "Tue", "we": "Wed", "th": "Thu", "fr": "Fri", "sa": "Sat", "su": "Sun"}


# ---------------------------------------------------------------- utilities
def _hm_to_min(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def _min_to_hm(v: int) -> str:
    v = max(0, min(v, 24 * 60))
    return f"{v // 60:02d}:{v % 60:02d}"


def _day_range(a: str, b: str) -> list[str]:
    i, j = DAYS.index(a), DAYS.index(b)
    if i <= j:
        return DAYS[i : j + 1]
    return DAYS[i:] + DAYS[: j + 1]  # wraps, e.g. Fr-Mo


def is_complete(weekly: dict | None) -> bool:
    return bool(weekly) and all(d in weekly for d in DAYS)


def to_matrix(weekly: dict | None) -> list[list[int | None]]:
    """7 x 24 matrix of 1 (open), 0 (closed) or None (unknown)."""
    m: list[list[int | None]] = [[None] * 24 for _ in range(7)]
    if not weekly:
        return m
    for di, d in enumerate(DAYS):
        if d in weekly:
            for h in range(24):
                m[di][h] = 0
    for di, d in enumerate(DAYS):
        for start, end in weekly.get(d, []) or []:
            s, e = _hm_to_min(start), _hm_to_min(end)
            if e <= s:  # overnight
                e += 24 * 60
            # every hour slot that any part of [s, e) touches; slots past midnight spill into the next day
            for slot in range(s // 60, (e - 1) // 60 + 1):
                if slot < 24:
                    m[di][slot] = 1
                else:
                    m[(di + 1) % 7][slot - 24] = 1
    return m


def agreement(a: dict | None, b: dict | None) -> float | None:
    """Share of hours (over days both sources know) on which two schedules agree."""
    ma, mb = to_matrix(a), to_matrix(b)
    same = total = 0
    for d in range(7):
        for h in range(24):
            if ma[d][h] is None or mb[d][h] is None:
                continue
            total += 1
            same += ma[d][h] == mb[d][h]
    return round(same / total, 4) if total else None


def to_text(weekly: dict | None) -> str:
    """Compact OSM-style text, e.g. 'Mo-Fr 09:00-18:00; Sa 10:00-14:00; Su off'."""
    if not weekly:
        return ""
    def key(d):
        if d not in weekly:
            return None
        iv = weekly[d]
        return ",".join(f"{s}-{e}" for s, e in iv) if iv else "off"
    if all(key(d) == "00:00-24:00" for d in DAYS):
        return "24/7"
    parts, i = [], 0
    while i < 7:
        k = key(DAYS[i])
        j = i
        while j + 1 < 7 and key(DAYS[j + 1]) == k:
            j += 1
        if k is not None:
            label = DAY_LABEL_OSM[DAYS[i]] if i == j else f"{DAY_LABEL_OSM[DAYS[i]]}-{DAY_LABEL_OSM[DAYS[j]]}"
            parts.append(f"{label} {k}")
        i = j + 1
    return "; ".join(parts)


DAY_LABEL_OSM = {d: d.capitalize() for d in DAYS}


def normalise(weekly: dict) -> dict:
    out = {}
    for d in DAYS:
        if d in weekly:
            ivs = []
            for s, e in weekly[d] or []:
                s, e = _clean_hm(s), _clean_hm(e)
                if s is None or e is None or s == e and s != "00:00":
                    continue
                if s == "00:00" and e == "00:00":
                    e = "24:00"
                ivs.append([s, e])
            out[d] = sorted(ivs)
    return out


def _clean_hm(v) -> str | None:
    if v is None:
        return None
    m = re.match(r"^\s*(\d{1,2})(?::|\.)?(\d{2})?(?::\d{2})?\s*$", str(v))
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if h > 24 or mi > 59 or (h == 24 and mi):
        return None
    return f"{h:02d}:{mi:02d}"


# ------------------------------------------------- OSM opening_hours syntax
_OSM_DAY = {"mo": "mo", "tu": "tu", "we": "we", "th": "th", "fr": "fr", "sa": "sa", "su": "su"}
_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")


def parse_osm(value: str | None) -> tuple[dict | None, list[str]]:
    """Parse the common subset of the OSM opening_hours syntax.

    Returns (weekly, warnings). Unsupported rules (month/date ranges, week numbers,
    public-holiday-only rules) are skipped with a warning. Later rules override
    earlier rules for the days they name, as in the OSM specification.
    """
    warnings: list[str] = []
    if not value or not value.strip():
        return None, ["empty"]
    v = value.strip().replace("–", "-").replace("—", "-")
    v = re.sub(r'"[^"]*"', "", v)  # comments
    if v.lower() in ("24/7", "24/7 open", "open 24/7"):
        return {d: [["00:00", "24:00"]] for d in DAYS}, warnings
    weekly: dict = {}
    rules = re.split(r";|\|\|", v)
    for raw in rules:
        rule = raw.strip()
        if not rule:
            continue
        low = rule.lower()
        if low.startswith(_MONTHS) or re.match(r"^\d{4}", low) or low.startswith("week"):
            warnings.append(f"skipped seasonal rule: {rule}")
            continue
        m = re.match(r"^((?:(?:mo|tu|we|th|fr|sa|su|ph|sh)(?:\[[^\]]*\])?(?:\s*-\s*(?:mo|tu|we|th|fr|sa|su))?\s*,?\s*)+)(.*)$", low)
        if m and re.match(r"^(mo|tu|we|th|fr|sa|su|ph|sh)\b", low):
            daypart, rest = m.group(1), m.group(2).strip()
        else:
            daypart, rest = "", low
        days: list[str] = []
        only_holiday = bool(daypart)
        for tok in re.split(r"\s*,\s*", daypart.strip().strip(",")) if daypart else []:
            tok = re.sub(r"\[[^\]]*\]", "", tok).strip()
            if not tok:
                continue
            if tok in ("ph", "sh"):
                continue
            only_holiday = False
            if "-" in tok:
                a, b = [t.strip() for t in tok.split("-", 1)]
                if a in _OSM_DAY and b in _OSM_DAY:
                    days += _day_range(a, b)
            elif tok in _OSM_DAY:
                days.append(tok)
        if daypart and only_holiday:
            warnings.append(f"skipped holiday rule: {rule}")
            continue
        if not daypart:
            days = list(DAYS)
        rest = rest.strip().strip(",").strip()
        if rest in ("off", "closed"):
            for d in days:
                weekly[d] = []
            continue
        if rest in ("24/7", ""):
            if rest == "24/7" or daypart:
                for d in days:
                    weekly[d] = [["00:00", "24:00"]] if rest == "24/7" else weekly.get(d, [["00:00", "24:00"]])
                if rest == "" and daypart:
                    warnings.append(f"day selector without times treated as 24h: {rule}")
            continue
        rest = rest.replace("sunrise", "07:00").replace("sunset", "19:00")
        ivs = []
        for span in re.split(r"\s*,\s*", rest):
            span = span.strip()
            mm = re.match(r"^(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})(?:\+)?$", span)
            if mm:
                ivs.append([_clean_hm(mm.group(1)), _clean_hm(mm.group(2))])
                continue
            mm = re.match(r"^(\d{1,2}:\d{2})\+$", span)
            if mm:
                ivs.append([_clean_hm(mm.group(1)), "24:00"])
                warnings.append("open-ended time treated as until midnight")
                continue
            warnings.append(f"unparsed time span: {span}")
        ivs = [iv for iv in ivs if iv[0] and iv[1]]
        if ivs:
            for d in days:
                weekly[d] = ivs
    if not weekly:
        return None, warnings or ["nothing parsed"]
    return normalise(weekly), warnings


# --------------------------------------------- free text (web pages) parser
_DAY_WORDS = [
    ("mo", r"mon(?:day)?s?"), ("tu", r"tue(?:s(?:day)?)?s?"), ("we", r"wed(?:nesday)?s?"),
    ("th", r"thu(?:r(?:s(?:day)?)?)?s?"), ("fr", r"fri(?:day)?s?"), ("sa", r"sat(?:urday)?s?"),
    ("su", r"sun(?:day)?s?"),
]
_DAY_RE = "|".join(f"(?P<{k}>{p})" for k, p in _DAY_WORDS)
_ONE_DAY = re.compile(rf"\b(?:{_DAY_RE})\b\.?", re.I)
_TIME = r"(?:\d{4}\s*(?:hrs|hr|h)\b|\d{1,2}(?:[:.]\d{2})?\s*(?:am\b|pm\b|a\.m\.|p\.m\.|nn\b|noon\b|hrs\b|h\b)?|noon|midnight)"
_TIME_RANGE = re.compile(rf"(?P<a>{_TIME})\s*(?:-|–|—|~|to|till|until)\s*(?P<b>{_TIME})", re.I)
_GROUP_WORDS = [
    (re.compile(r"\b(daily|every\s*day|everyday|7 days a week|all days|mon(?:day)?\s*(?:-|–|to)\s*sun(?:day)?)\b", re.I), DAYS),
    (re.compile(r"\b(weekdays?)\b", re.I), DAYS[:5]),
    (re.compile(r"\b(weekends?)\b", re.I), DAYS[5:]),
]
HOURS_KEYWORDS = re.compile(
    r"opening hours|operating hours|business hours|open(?:ing)? times|hours of operation|store hours|"
    r"\bhours\b|\bopen\b|\bdaily\b|\bclosed\b|mon(?:day)?\b|\bweekdays?\b|24 hours", re.I)


def _parse_time(tok: str, is_end: bool = False, ref_ampm: str | None = None) -> int | None:
    t = tok.strip().lower().replace(" ", "").replace("a.m.", "am").replace("p.m.", "pm")
    if t in ("noon", "12nn", "12noon"):
        return 12 * 60
    if t == "midnight":
        return 24 * 60 if is_end else 0
    m4 = re.match(r"^(\d{2})(\d{2})(?:hrs|hr|h)$", t)  # Singapore style "1000hrs"
    if m4:
        h, mi = int(m4.group(1)), int(m4.group(2))
        return h * 60 + mi if h <= 24 and mi < 60 else None
    m = re.match(r"^(\d{1,2})(?:[:.](\d{2}))?(am|pm|nn|noon|hrs|h)?$", t)
    if not m:
        return None
    h, mi, suf = int(m.group(1)), int(m.group(2) or 0), m.group(3) or ref_ampm
    if suf in ("hrs", "h"):
        suf = None
        if m.group(2) is None:
            return h * 60 if h <= 24 else None
    if mi > 59:
        return None
    if suf in ("nn", "noon"):
        return 12 * 60 + mi if h == 12 else None
    if suf == "am":
        if h > 12:
            return None
        h = 0 if h == 12 else h
        if is_end and h == 0 and mi == 0:
            return 24 * 60
    elif suf == "pm":
        if h > 12:
            return None
        h = 12 if h == 12 else h + 12
    elif suf is None and len(m.group(1)) <= 2 and m.group(2) is None:
        # bare number like "9-6": too ambiguous unless 24h with hrs suffix
        return None
    if h > 24:
        return None
    return h * 60 + mi


_SUF = re.compile(r"(am|pm|a\.m\.|p\.m\.)", re.I)


def _parse_range(a_raw: str, b_raw: str) -> list[str] | None:
    a_suf, b_suf = _SUF.search(a_raw), _SUF.search(b_raw)
    b = _parse_time(b_raw, is_end=True)
    if a_suf or not b_suf:
        a = _parse_time(a_raw)
    else:
        # "9-5pm" / "6-10pm": borrow the end's suffix, fall back to am if that is after the end
        suf = b_suf.group(1).lower().replace(".", "")
        a = _parse_time(a_raw, ref_ampm=suf)
        if a is not None and b is not None and suf == "pm" and a >= b:
            a = _parse_time(a_raw, ref_ampm="am")
    if a is None or b is None or a == b or a >= 24 * 60:
        return None
    return [_min_to_hm(a), "24:00" if b >= 24 * 60 else _min_to_hm(b)]


def _days_in(segment: str) -> tuple[list[str], int]:
    """Return days referenced at the start of a segment and the end index of that day text."""
    best: list[str] = []
    end = 0
    for rx, days in _GROUP_WORDS:
        m = rx.search(segment)
        if m and m.start() < 40:
            best, end = list(days), m.end()
            break
    if not best:
        tokens = [t for t in _ONE_DAY.finditer(segment) if t.start() < 60]
        if tokens:
            # keep only the contiguous day expression, e.g. "Mon, Wed & Fri" or "Tue-Sun"
            chain = [tokens[0]]
            for t in tokens[1:]:
                gap = segment[chain[-1].end():t.start()]
                if re.fullmatch(r"\s*(?:-|to|till|through|thru|,|&|and|/)?\s*", gap, re.I):
                    chain.append(t)
                else:
                    break
            tokens = chain
            days: list[str] = []
            i = 0
            while i < len(tokens):
                d1 = next(k for k, v in tokens[i].groupdict().items() if v)
                between = segment[tokens[i].end() : tokens[i + 1].start()] if i + 1 < len(tokens) else ""
                if i + 1 < len(tokens) and re.fullmatch(r"\s*(?:-|to|till|through|thru)\s*", between, re.I):
                    d2 = next(k for k, v in tokens[i + 1].groupdict().items() if v)
                    days += _day_range(d1, d2)
                    end = tokens[i + 1].end()
                    i += 2
                else:
                    days.append(d1)
                    end = tokens[i].end()
                    i += 1
            best = list(dict.fromkeys(days))
    # strip "& PH" / "and public holidays" noise is harmless; holidays ignored
    return best, end


_CN_DAYS = [("一", "Monday"), ("二", "Tuesday"), ("三", "Wednesday"), ("四", "Thursday"), ("五", "Friday"),
            ("六", "Saturday"), ("日", "Sunday"), ("天", "Sunday")]


def normalise_cn(text: str) -> str:
    """Turn Chinese-language hours (e.g. a Chinese Google listing) into English the parser understands."""
    if not re.search(r"[\u4e00-\u9fff]", text or ""):
        return text
    t = text.replace("：", ":").replace("～", "-").replace("至", "-").replace("，", ",").replace("；", ";")
    for cn, en in _CN_DAYS:
        t = re.sub(rf"(?:星期|周|礼拜){cn}", en, t)
    t = re.sub(r"(?:24\s*小时营业|营业\s*24\s*小时|全天营业|24\s*小时)", " Open 24 hours ", t)
    t = re.sub(r"休息|休业|不营业|关闭|闭店|已打烊", " Closed ", t)
    t = re.sub(r"每天|每日", " Daily ", t)
    t = re.sub(r"工作日", " Weekdays ", t)
    t = re.sub(r"周末", " Weekends ", t)

    def ampm(m):
        word, hh, mm = m.group(1), int(m.group(2)), m.group(3) or "00"
        if word in ("上午", "早上", "凌晨"):
            suf = "am"
        elif word == "中午":
            suf = "pm" if hh == 12 or hh < 3 else "am"
        else:  # 下午 / 晚上 / 傍晚
            suf = "pm"
        if word == "凌晨" and hh == 12:
            return f"12:{mm}am"
        return f"{hh}:{mm}{suf}"
    t = re.sub(r"午夜\s*(?:12(?:[:点]00)?)?|半夜\s*12(?:[:点]00)?", "12:00am", t)
    t = re.sub(r"(上午|早上|凌晨|中午|下午|晚上|傍晚)\s*(\d{1,2})(?:[:点](\d{2}))?", ampm, t)
    t = re.sub(r"(\d{1,2}):(\d{2})(am|pm)", r"\1:\2\3", t)
    return t


def parse_any(text: str) -> dict:
    """Pasted text from any source: try OSM syntax, then free text (English or Chinese)."""
    w, warn = parse_osm(text) if re.fullmatch(r"[\sA-Za-z0-9:,;\-/+]+", (text or "").strip()) else (None, [])
    if w and is_complete(w):
        return {"weekly": w, "confidence": 0.9, "evidence": text.strip()[:600], "notes": warn}
    return parse_text(text)


def parse_text(text: str) -> dict:
    """Rule-based extraction of a weekly schedule from free text.

    Returns {"weekly": dict|None, "confidence": float, "evidence": str, "notes": [...]}.
    Confidence is low when times are found without any day words.
    """
    notes: list[str] = []
    if not text:
        return {"weekly": None, "confidence": 0.0, "evidence": "", "notes": ["no text"]}
    t = normalise_cn(text).replace("–", "-").replace("—", "-").replace("\xa0", " ").replace(" ", " ")
    t = re.sub(r"[ \t]+", " ", t)
    segments = [s.strip() for s in re.split(r"[\n|;•]+|(?<=[a-z0-9])\.\s+(?=[A-Z])|(?<=[0-9mMdD])\s*,\s*(?=(?i:mon|tue|wed|thu|fri|sat|sun|daily|week|public|ph\b|closed))", t) if s.strip()]
    weekly: dict = {}
    evidence: list[str] = []
    timed_without_days: list[list[list[str]]] = []
    pending_days: list[str] = []
    for seg in segments:
        if len(seg) > 300:
            continue
        low = seg.lower()
        days, dend = _days_in(seg)
        if re.search(r"public holiday|\bph\b|eve of", low) and not days:
            continue
        if "24 hours" in low or "24hrs" in low.replace(" ", "") or "open 24" in low:
            tgt = days or (pending_days if pending_days else None)
            if tgt is None and re.search(r"open 24 hours|24 hours daily|24/7", low):
                tgt = list(DAYS)
            if tgt:
                for d in tgt:
                    weekly[d] = [["00:00", "24:00"]]
                evidence.append(seg)
                pending_days = []
                continue
        ranges = []
        for m in _TIME_RANGE.finditer(seg):
            iv = _parse_range(m.group("a"), m.group("b"))
            if iv:
                ranges.append(iv)
        is_closed = bool(re.search(r"\bclosed\b|\boff\b", low)) and not ranges
        if days and is_closed:
            for d in days:
                weekly[d] = []
            evidence.append(seg)
            pending_days = []
            continue
        if days and ranges:
            for d in days:
                weekly[d] = ranges
            evidence.append(seg)
            pending_days = []
        elif days and not ranges:
            pending_days = days  # e.g. "Monday - Friday" on one line, times on the next
        elif ranges and pending_days:
            for d in pending_days:
                weekly[d] = ranges
            evidence.append(seg)
            pending_days = []
        elif ranges:
            timed_without_days.append(ranges)
            evidence.append(seg)
    conf = 0.0
    if weekly:
        conf = 0.6 if len(weekly) >= 5 else 0.45
        if len(weekly) < 7:
            notes.append("some days not stated")
    elif timed_without_days and HOURS_KEYWORDS.search(t):
        weekly = {d: timed_without_days[0] for d in DAYS}
        conf = 0.3
        notes.append("times found without day names; assumed daily")
    if not weekly:
        return {"weekly": None, "confidence": 0.0, "evidence": "", "notes": notes or ["no schedule found"]}
    return {"weekly": normalise(weekly), "confidence": conf, "evidence": " | ".join(evidence)[:600], "notes": notes}


# ------------------------------------------------ schema.org / Google
_SCHEMA_DAY = {"monday": "mo", "tuesday": "tu", "wednesday": "we", "thursday": "th",
               "friday": "fr", "saturday": "sa", "sunday": "su"}


def from_schema_spec(specs) -> dict | None:
    """schema.org openingHoursSpecification (list of dicts) → weekly."""
    if isinstance(specs, dict):
        specs = [specs]
    weekly: dict = {}
    for s in specs or []:
        if not isinstance(s, dict):
            continue
        dows = s.get("dayOfWeek")
        if isinstance(dows, str):
            dows = [dows]
        o, c = _clean_hm(s.get("opens")), _clean_hm(s.get("closes"))
        for dw in dows or []:
            key = _SCHEMA_DAY.get(str(dw).rsplit("/", 1)[-1].lower())
            if not key:
                continue
            weekly.setdefault(key, [])
            if o and c and not (o == "00:00" and c == "00:00" and s.get("closes") in ("00:00", "00:00:00") and s.get("opens") == s.get("closes") and False):
                if o == c == "00:00":
                    weekly[key].append(["00:00", "24:00"])
                elif o == c:
                    pass  # opens == closes → closed per schema.org convention
                else:
                    weekly[key].append([o, c])
    return normalise(weekly) if weekly else None


def from_google_periods(periods) -> dict | None:
    """Google Places regularOpeningHours.periods → weekly. Google day 0 = Sunday."""
    if not periods:
        return None
    gmap = ["su", "mo", "tu", "we", "th", "fr", "sa"]
    if len(periods) == 1 and "close" not in periods[0]:
        return {d: [["00:00", "24:00"]] for d in DAYS}
    weekly: dict = {d: [] for d in DAYS}
    for p in periods:
        o, c = p.get("open"), p.get("close")
        if not o:
            continue
        d = gmap[o.get("day", 0)]
        s = f"{o.get('hour', 0):02d}:{o.get('minute', 0):02d}"
        if c:
            e = f"{c.get('hour', 0):02d}:{c.get('minute', 0):02d}"
            if e == "00:00" and c.get("day") != o.get("day"):
                e = "24:00"
        else:
            e = "24:00"
        weekly[d].append([s, e])
    return normalise(weekly)
