"""Constants for the Magic Pass integration."""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

DOMAIN = "magic_pass"
# Single source of truth: the version in manifest.json (also cache-busts the card URL)
VERSION: str = json.loads((Path(__file__).parent / "manifest.json").read_text(encoding="utf-8"))["version"]

CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_LOCATION = "location"
CONF_MAX_TRAVEL = "max_travel"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_TRACKED = "tracked_stations"
CONF_LANGUAGE = "language"

DEFAULT_MAX_TRAVEL = 120  # minutes
DEFAULT_SCAN_INTERVAL = 30  # minutes
MIN_SCAN_INTERVAL = 15

SITE = "https://www.magicpass.ch"
MAP_URL = "https://map.magicpass.ch/markers?locale=fr-FR"
OSRM_URL = "https://router.project-osrm.org/table/v1/driving/{coords}?sources=0&annotations=duration"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

TTL_REGIONS = timedelta(days=7)
TTL_MAP = timedelta(days=7)
TTL_ROUTES = timedelta(days=14)
TTL_WEATHER = timedelta(hours=1)

STORAGE_VERSION = 1
STORAGE_KEY = "magic_pass.cache"

EVENT_STATION_OPENED = "magic_pass_station_opened"

CARD_URL = "/magic_pass/magic-pass-card.js"

ATTRIBUTION = "Données : magicpass.ch, OpenStreetMap/OSRM, Open-Meteo"
