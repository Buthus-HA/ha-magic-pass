"""Data update coordinator for Magic Pass."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import json
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import parser
from .const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MAX_TRAVEL,
    CONF_SCAN_INTERVAL,
    DEFAULT_MAX_TRAVEL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_STATION_OPENED,
    MAP_URL,
    OPEN_METEO_URL,
    OSRM_URL,
    SITE,
    STORAGE_KEY,
    STORAGE_VERSION,
    TTL_MAP,
    TTL_REGIONS,
    TTL_ROUTES,
    TTL_WEATHER,
)

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "HomeAssistant-MagicPass/0.1 (+https://www.home-assistant.io)",
    "Accept-Language": "fr-CH,fr;q=0.9",
}
TIMEOUT = aiohttp.ClientTimeout(total=60)


def option(entry: ConfigEntry, key: str, default: Any) -> Any:
    """Read a setting from options first, then data."""
    return entry.options.get(key, entry.data.get(key, default))


class MagicPassCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch and combine Magic Pass data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=option(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        )
        self.session = async_get_clientsession(hass)
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}")
        self._cache: dict[str, Any] | None = None
        self._open_slugs: set[str] | None = None
        self._ski_slugs: set[str] | None = None

    # ------------------------------------------------------------------ helpers
    @property
    def home(self) -> tuple[float, float]:
        """Starting point for travel times."""
        entry = self.config_entry
        return (
            float(option(entry, CONF_LATITUDE, self.hass.config.latitude)),
            float(option(entry, CONF_LONGITUDE, self.hass.config.longitude)),
        )

    @property
    def max_travel(self) -> int:
        """Maximum travel time for the 'best resort' sensor."""
        return int(option(self.config_entry, CONF_MAX_TRAVEL, DEFAULT_MAX_TRAVEL))

    def _fresh(self, key: str, ttl: timedelta) -> dict[str, Any] | None:
        assert self._cache is not None
        item = self._cache.get(key)
        if item and dt_util.utcnow().timestamp() - item.get("t", 0) < ttl.total_seconds():
            return item
        return None

    def _put(self, key: str, value: Any, **extra: Any) -> None:
        assert self._cache is not None
        self._cache[key] = {"t": dt_util.utcnow().timestamp(), "v": value, **extra}

    async def _get_text(self, url: str) -> str:
        async with self.session.get(url, headers=HEADERS, timeout=TIMEOUT) as resp:
            resp.raise_for_status()
            return await resp.text()

    async def _get_json(self, url: str, **kwargs: Any) -> Any:
        method = "POST" if "json" in kwargs else "GET"
        async with self.session.request(method, url, headers=HEADERS, timeout=TIMEOUT, **kwargs) as resp:
            resp.raise_for_status()
            return json.loads(await resp.text())

    # ------------------------------------------------------------------ sources
    async def _regions(self, page: str) -> dict[str, str]:
        if cached := self._fresh("regions", TTL_REGIONS):
            return cached["v"]
        result: dict[str, str] = {}
        for region_id, label in parser.parse_region_filters(page):
            try:
                text = await self._get_text(f"{SITE}/fr/stations/opening?states%5B%5D={region_id}")
            except (aiohttp.ClientError, TimeoutError) as err:
                _LOGGER.debug("Region %s: %s", label, err)
                continue
            for row in parser.parse_rows(text):
                result[row["slug"]] = label
            await asyncio.sleep(0.3)
        if result:
            self._put("regions", result)
        return result or (self._cache or {}).get("regions", {}).get("v", {})

    async def _map(self) -> dict[str, Any]:
        if cached := self._fresh("map", TTL_MAP):
            return cached["v"]
        try:
            features = await self._get_json(MAP_URL, json={"mutations": []})
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            _LOGGER.warning("Magic Pass map unavailable: %s", err)
            old = (self._cache or {}).get("map")
            return old["v"] if old else {"destinations": {}, "stats": {}}
        data = parser.parse_map(features)
        stats = await self.hass.async_add_executor_job(
            parser.trail_stats, data["destinations"], data["trails"]
        )
        value = {"destinations": data["destinations"], "stats": stats}
        self._put("map", value)
        return value

    async def _routes(self, points: list[tuple[float, float]]) -> tuple[list[int | None], str]:
        home = self.home
        key = f"{home[0]:.3f},{home[1]:.3f}|" + ";".join(f"{p[0]:.3f},{p[1]:.3f}" for p in points)
        cached = self._fresh("routes", TTL_ROUTES)
        if cached and cached.get("k") == key:
            return cached["v"], "osrm"
        coords = ";".join([f"{home[1]:.5f},{home[0]:.5f}"] + [f"{p[1]:.5f},{p[0]:.5f}" for p in points])
        try:
            data = await self._get_json(OSRM_URL.format(coords=coords))
            durations = data["durations"][0][1:]
            value = [round(d / 60) if d is not None else None for d in durations]
            self._put("routes", value, k=key)
            return value, "osrm"
        except (aiohttp.ClientError, TimeoutError, KeyError, ValueError) as err:
            _LOGGER.info("OSRM unavailable, estimating travel times: %s", err)
            return [
                round(parser.haversine(home[0], home[1], lat, lon) * 1.45 / 55 * 60) for lat, lon in points
            ], "estimate"

    async def _weather(self, points: list[tuple[float, float]]) -> list[dict[str, Any] | None]:
        key = ";".join(f"{p[0]:.3f},{p[1]:.3f}" for p in points)
        cached = self._fresh("weather", TTL_WEATHER)
        if cached and cached.get("k") == key:
            return cached["v"]
        result: list[dict[str, Any] | None] = []
        now_hour = dt_util.now(dt_util.get_time_zone("Europe/Zurich")).strftime("%Y-%m-%dT%H:00")
        for start in range(0, len(points), 50):
            chunk = points[start : start + 50]
            params = {
                "latitude": ",".join(f"{p[0]:.4f}" for p in chunk),
                "longitude": ",".join(f"{p[1]:.4f}" for p in chunk),
                "daily": "snowfall_sum,weather_code,temperature_2m_max,temperature_2m_min",
                "hourly": "snowfall",
                "past_days": "3",
                "forecast_days": "2",
                "timezone": "Europe/Zurich",
            }
            try:
                payload = await self._get_json(OPEN_METEO_URL, params=params)
                result.extend(parser.parse_weather(payload, now_hour))
            except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                _LOGGER.info("Open-Meteo unavailable: %s", err)
                result.extend([None] * len(chunk))
        self._put("weather", result, k=key)
        return result

    # ------------------------------------------------------------------ update
    async def _async_update_data(self) -> dict[str, Any]:
        if self._cache is None:
            self._cache = await self._store.async_load() or {}
        try:
            page = await self._get_text(f"{SITE}/fr/stations/opening")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"magicpass.ch unreachable: {err}") from err
        rows = parser.parse_rows(page)
        if not rows:
            raise UpdateFailed("No resort found on magicpass.ch (page layout changed?)")

        regions = await self._regions(page)
        map_data = await self._map()
        destinations = map_data.get("destinations", {})
        stats = map_data.get("stats", {})
        today = dt_util.now().date()

        stations: list[dict[str, Any]] = []
        points: list[tuple[float, float]] = []
        with_coords: list[int] = []
        for row in rows:
            dest = parser.match_destination(row["slug"], destinations)
            lat, lon = destinations[dest] if dest else (None, None)
            trail = stats.get(dest, {"n": 0, "vb": 0}) if dest else {"n": 0, "vb": 0}
            opened = parser.is_open(row["state"])
            station = {
                "name": row["name"],
                "slug": row["slug"],
                "url": f"{SITE}/fr/stations/{row['slug']}",
                "region": regions.get(row["slug"], ""),
                "state": row["state"],
                "kind": row["kind"],
                "open": opened,
                "opening": parser.next_opening(row["info"], today),
                "info": row["info"][:220],
                "lifts_open": row["lifts_open"],
                "lifts_total": row["lifts_total"],
                "km_open": row["km_open"],
                "km_total": row["km_total"],
                "pct_open": parser.percent_open(row, opened),
                "trails": trail["n"],
                "vb": round(100 * trail["vb"] / trail["n"]) if trail["n"] else None,
                "lat": lat,
                "lon": lon,
                "travel": None,
                "weather": None,
            }
            stations.append(station)
            if lat is not None:
                with_coords.append(len(stations) - 1)
                points.append((lat, lon))

        travel, travel_source = await self._routes(points) if points else ([], "")
        weather = await self._weather(points) if points else []
        for pos, idx in enumerate(with_coords):
            stations[idx]["travel"] = travel[pos] if pos < len(travel) else None
            stations[idx]["weather"] = weather[pos] if pos < len(weather) else None
        for station in stations:
            station["score"] = parser.score(station)
        stations.sort(key=lambda s: (s["travel"] is None, s["travel"] or 0, s["name"]))

        await self._store.async_save(self._cache)

        opened = [s for s in stations if s["open"]]
        near = [s for s in opened if s["travel"] is not None and s["travel"] <= self.max_travel]
        best = max(near, key=lambda s: s["score"]) if near else None

        open_slugs = {s["slug"] for s in opened}
        ski_slugs = {s["slug"] for s in opened if not parser.is_pedestrian(s)}
        if self._open_slugs is not None:
            for station in opened:
                pedestrian = parser.is_pedestrian(station)
                newly_open = station["slug"] not in self._open_slugs
                # also fire when a pedestrian-only resort opens its slopes
                newly_ski = not pedestrian and station["slug"] not in (self._ski_slugs or set())
                if newly_open or newly_ski:
                    self.hass.bus.async_fire(
                        EVENT_STATION_OPENED,
                        {
                            "name": station["name"],
                            "slug": station["slug"],
                            "region": station["region"],
                            "travel": station["travel"],
                            "lifts": f"{station['lifts_open']}/{station['lifts_total']}",
                            "km": f"{station['km_open']}/{station['km_total']}",
                            "url": station["url"],
                            "pedestrian": pedestrian,
                            "kind": station.get("kind", ""),
                        },
                    )
        self._open_slugs = open_slugs
        self._ski_slugs = ski_slugs

        return {
            "updated": dt_util.utcnow().isoformat(timespec="seconds"),
            "home": list(self.home),
            "max_travel": self.max_travel,
            "travel_source": travel_source,
            "count": len(stations),
            "open": len(opened),
            "open_near": len(near),
            "best": best,
            "stations": stations,
        }

    def station(self, slug: str) -> dict[str, Any] | None:
        """Return one station by slug."""
        for station in (self.data or {}).get("stations", []):
            if station["slug"] == slug:
                return station
        return None


def utc_from_iso(value: str | None) -> datetime | None:
    """Parse an ISO timestamp."""
    return dt_util.parse_datetime(value) if value else None
