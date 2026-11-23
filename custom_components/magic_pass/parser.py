"""Pure parsing and scoring helpers (no Home Assistant imports, easy to test)."""
from __future__ import annotations

from datetime import date
import html
import math
import re
from typing import Any

WMO: dict[int, tuple[str, str, float]] = {
    0: ("☀️", "clear", 1.0), 1: ("🌤️", "mainly_clear", 0.9), 2: ("⛅", "partly_cloudy", 0.7),
    3: ("☁️", "overcast", 0.5), 45: ("🌫️", "fog", 0.3), 48: ("🌫️", "fog", 0.3),
    51: ("🌦️", "drizzle", 0.3), 53: ("🌦️", "drizzle", 0.3), 55: ("🌧️", "drizzle", 0.2),
    56: ("🌧️", "freezing_drizzle", 0.1), 57: ("🌧️", "freezing_drizzle", 0.1),
    61: ("🌧️", "rain", 0.2), 63: ("🌧️", "rain", 0.1), 65: ("🌧️", "heavy_rain", 0.0),
    66: ("🌧️", "freezing_rain", 0.0), 67: ("🌧️", "freezing_rain", 0.0),
    71: ("🌨️", "light_snow", 0.6), 73: ("🌨️", "snow", 0.5), 75: ("❄️", "heavy_snow", 0.4),
    77: ("🌨️", "snow_grains", 0.5), 80: ("🌦️", "showers", 0.3), 81: ("🌧️", "showers", 0.2),
    82: ("⛈️", "heavy_showers", 0.0), 85: ("🌨️", "snow_showers", 0.5),
    86: ("❄️", "snow_showers", 0.4), 95: ("⛈️", "thunderstorm", 0.0),
    96: ("⛈️", "thunderstorm", 0.0), 99: ("⛈️", "thunderstorm", 0.0),
}

_ROW_RE = re.compile(
    r'<a href="/fr/stations/(?P<slug>[^"]+)"[^>]*aria-label="(?P<name>[^"]+)"[^>]*>(?P<body>.*?)</a>',
    re.S,
)
_REGION_RE = re.compile(
    r'name="states\[\]"[^>]*?id="filter-(\d+)"[^>]*>.*?<label[^>]*for="filter-\1"[^>]*>\s*([^<]+?)\s*</label>',
    re.S,
)
_DATE_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?")


def strip_tags(value: str) -> str:
    """Turn an HTML fragment into one line of text."""
    value = re.sub(r"</p>\s*<p>", " · ", value)
    value = re.sub(r"<br\s*/?>", " · ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip(" ·")


def parse_rows(page: str) -> list[dict[str, Any]]:
    """Parse the station rows of magicpass.ch/fr/stations/opening."""
    block_match = re.search(r"<bd-resorts-opening.*?</bd-resorts-opening>", page, re.S)
    block = block_match.group(0) if block_match else page
    rows: list[dict[str, Any]] = []
    for row in _ROW_RE.finditer(block):
        body = row.group("body")
        state = re.search(r'class="opening-state[^"]*"[^>]*>(.*?)</div>', body, re.S)
        marker = re.search(r"marker-icon--(?!sm\b|md\b|lg\b)([\w-]+)", body)
        info = re.search(r'<span class="text-gray-500[^"]*"[^>]*>(.*?)</span>\s*</span>', body, re.S)
        lifts = re.search(r"Installations ouvertes</small>\s*<span[^>]*>\s*(\d+)\s*/\s*(\d+)", body)
        km = re.search(r"Pistes ouvertes</small>\s*<span[^>]*>\s*([\d.]+)\s*/\s*([\d.]+)", body)
        rows.append(
            {
                "name": html.unescape(row.group("name")).strip(),
                "slug": row.group("slug"),
                "state": strip_tags(state.group(1)) if state else "?",
                "kind": marker.group(1) if marker else "",
                "info": strip_tags(info.group(1)) if info else "",
                "lifts_open": int(lifts.group(1)) if lifts else 0,
                "lifts_total": int(lifts.group(2)) if lifts else 0,
                "km_open": float(km.group(1)) if km else 0.0,
                "km_total": float(km.group(2)) if km else 0.0,
            }
        )
    return rows


def parse_region_filters(page: str) -> list[tuple[str, str]]:
    """Return (filter id, region label) pairs from the opening page."""
    return [(rid, label.strip()) for rid, label in _REGION_RE.findall(page)]


def compact(value: str) -> str:
    """Lower-case ASCII letters only, for fuzzy slug matching."""
    value = value.lower()
    for src, dst in (
        ("à", "a"), ("â", "a"), ("ä", "a"), ("é", "e"), ("è", "e"), ("ê", "e"), ("ë", "e"),
        ("î", "i"), ("ï", "i"), ("ô", "o"), ("ö", "o"), ("û", "u"), ("ü", "u"), ("ç", "c"),
    ):
        value = value.replace(src, dst)
    return re.sub(r"[^a-z]", "", value)


def match_destination(slug: str, destinations: dict[str, list[float]]) -> str | None:
    """Match an opening-page slug (e.g. 'charmey-14') to a map destination key."""
    core = compact(re.sub(r"-\d+$", "", slug))
    compacted = {key: compact(key) for key in destinations}
    for key, value in compacted.items():
        if value == core:
            return key
    best, best_len = None, 0
    for key, value in compacted.items():
        if core and (core in value or value in core):
            length = min(len(core), len(value))
            if length > best_len:
                best, best_len = key, length
    return best if best_len >= 5 else None


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def parse_map(features: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract destinations and ski trails from map.magicpass.ch markers."""
    destinations: dict[str, list[float]] = {}
    trails: list[list[Any]] = []
    for feature in features:
        props = feature.get("properties") or {}
        coords = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]
        family, category = props.get("family"), props.get("category")
        if family == "destinations":
            destinations[str(props.get("objectId", "")).split("/", 1)[-1]] = [lat, lon]
        elif family == "ski_trail" and category in (
            "ski_novice", "ski_easy", "ski_intermediate", "ski_advanced"
        ):
            trails.append([lat, lon, category])
    return {"destinations": destinations, "trails": trails}


def trail_stats(destinations: dict[str, list[float]], trails: list[list[Any]]) -> dict[str, dict[str, int]]:
    """Assign each trail to the nearest destination (< 15 km)."""
    stats = {key: {"n": 0, "vb": 0} for key in destinations}
    for lat, lon, category in trails:
        best, best_d = None, 15.0
        for key, (dlat, dlon) in destinations.items():
            dist = haversine(lat, lon, dlat, dlon)
            if dist < best_d:
                best, best_d = key, dist
        if best:
            stats[best]["n"] += 1
            if category in ("ski_novice", "ski_easy"):
                stats[best]["vb"] += 1
    return stats


def next_opening(info: str, today: date) -> str:
    """Next winter opening date (dd.mm) mentioned in the opening text."""
    best: date | None = None
    for match in _DATE_RE.finditer(info or ""):
        day, month = int(match.group(1)), int(match.group(2))
        if not (1 <= day <= 31 and 1 <= month <= 12) or 5 <= month <= 10:
            continue
        year = int(match.group(3)) if match.group(3) else today.year
        if year < 100:
            year += 2000
        try:
            found = date(year, month, day)
            if not match.group(3) and found < today:
                found = date(year + 1, month, day)
        except ValueError:
            continue
        if found >= today and (best is None or found < best):
            best = found
    return best.strftime("%d.%m") if best else ""


def is_open(state: str) -> bool:
    """Whether a Magic Pass opening state means at least partly open."""
    return state.lower().startswith(("ouvert", "partiel"))


def percent_open(row: dict[str, Any], opened: bool) -> int:
    """Share of the resort open, from km of slopes or lifts."""
    if not opened:
        return 0
    if row["km_total"] and row["km_open"]:
        return round(100 * row["km_open"] / row["km_total"])
    if row["lifts_total"]:
        return round(100 * row["lifts_open"] / row["lifts_total"])
    return 100


def score(station: dict[str, Any]) -> float:
    """Score 0-10: 40 % opening, 30 % fresh snow, 20 % weather, 10 % travel."""
    if not station["open"]:
        return 0.0
    total = 4.0 * station["pct_open"] / 100.0
    weather = station.get("weather") or {}
    total += 3.0 * min((weather.get("snow72") or 0) / 20.0, 1.0)
    total += 2.0 * WMO.get(weather.get("code"), ("", "", 0.5))[2]
    travel = station.get("travel")
    if travel is not None:
        total += 1.0 if travel <= 60 else 0.5 if travel <= 120 else 0.0
    return round(min(total, 10.0), 1)


def parse_weather(payload: Any, now_hour: str) -> list[dict[str, Any] | None]:
    """Parse an Open-Meteo multi-location response."""
    items = payload if isinstance(payload, list) else [payload]
    out: list[dict[str, Any] | None] = []
    for item in items:
        try:
            hours = item["hourly"]["time"]
            snow = item["hourly"]["snowfall"]
            end = hours.index(now_hour) if now_hour in hours else len(hours) - 1
            snow72 = sum(x or 0 for x in snow[max(0, end - 72) : end + 1])
            daily = item["daily"]
            today_idx = 3 if len(daily["time"]) > 3 else len(daily["time"]) - 1
            code = daily["weather_code"][today_idx]
            icon, label, _ = WMO.get(code, ("❔", "unknown", 0.5))
            out.append(
                {
                    "snow72": round(snow72),
                    "code": code,
                    "icon": icon,
                    "label": label,
                    "tmax": daily["temperature_2m_max"][today_idx],
                    "tmin": daily["temperature_2m_min"][today_idx],
                    "snow_tomorrow": round(daily["snowfall_sum"][today_idx + 1] or 0)
                    if today_idx + 1 < len(daily["time"])
                    else 0,
                }
            )
        except (KeyError, IndexError, TypeError, ValueError):
            out.append(None)
    return out
