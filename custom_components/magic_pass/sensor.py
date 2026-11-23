"""Sensors for Magic Pass."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import MagicPassConfigEntry
from .const import ATTRIBUTION, CONF_TRACKED, DOMAIN
from .coordinator import MagicPassCoordinator, utc_from_iso

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class MagicPassSensorDescription(SensorEntityDescription):
    """Describe a summary sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _best_attrs(data: dict[str, Any]) -> dict[str, Any]:
    best = data.get("best")
    if not best:
        return {}
    return {
        "score": best["score"],
        "travel_min": best["travel"],
        "region": best["region"],
        "lifts": f"{best['lifts_open']}/{best['lifts_total']}",
        "km": f"{best['km_open']}/{best['km_total']}",
        "url": best["url"],
    }


SUMMARY: tuple[MagicPassSensorDescription, ...] = (
    MagicPassSensorDescription(
        key="open_resorts",
        translation_key="open_resorts",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["open"],
        attrs_fn=lambda d: {
            "total": d["count"],
            "open_within_max_travel": d["open_near"],
            "open_resorts": ", ".join(s["name"] for s in d["stations"] if s["open"])[:250],
        },
    ),
    MagicPassSensorDescription(
        key="open_near",
        translation_key="open_near",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["open_near"],
    ),
    MagicPassSensorDescription(
        key="best_resort",
        translation_key="best_resort",
        value_fn=lambda d: d["best"]["name"] if d.get("best") else None,
        attrs_fn=_best_attrs,
    ),
    MagicPassSensorDescription(
        key="best_score",
        translation_key="best_score",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["best"]["score"] if d.get("best") else 0,
    ),
    MagicPassSensorDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: utc_from_iso(d.get("updated")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MagicPassConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [MagicPassSummarySensor(coordinator, d) for d in SUMMARY]
    tracked = entry.options.get(CONF_TRACKED, [])
    entities += [MagicPassStationSensor(coordinator, slug) for slug in tracked if coordinator.station(slug)]
    async_add_entities(entities)


class MagicPassEntity(CoordinatorEntity[MagicPassCoordinator]):
    """Common base."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: MagicPassCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Magic Pass",
            manufacturer="Magic Pass (données publiques)",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.magicpass.ch/fr/stations/opening",
        )


class MagicPassSummarySensor(MagicPassEntity, SensorEntity):
    """Summary sensor."""

    entity_description: MagicPassSensorDescription

    def __init__(self, coordinator: MagicPassCoordinator, description: MagicPassSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)


class MagicPassStationSensor(MagicPassEntity, SensorEntity):
    """One resort the user chose to track."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["open", "partial", "closed"]
    _attr_translation_key = "station"

    def __init__(self, coordinator: MagicPassCoordinator, slug: str) -> None:
        super().__init__(coordinator)
        self._slug = slug
        station = coordinator.station(slug) or {}
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_station_{slug}"
        self._attr_translation_placeholders = {"name": station.get("name", slug)}

    @property
    def _station(self) -> dict[str, Any] | None:
        return self.coordinator.station(self._slug)

    @property
    def available(self) -> bool:
        return super().available and self._station is not None

    @property
    def native_value(self) -> str | None:
        station = self._station
        if not station:
            return None
        if not station["open"]:
            return "closed"
        return "partial" if station["state"].lower().startswith("partiel") else "open"

    @property
    def icon(self) -> str:
        return "mdi:ski" if self.native_value in ("open", "partial") else "mdi:ski-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        s = self._station
        if not s:
            return None
        weather = s.get("weather") or {}
        return {
            "resort": s["name"],
            "region": s["region"],
            "lifts_open": s["lifts_open"],
            "lifts_total": s["lifts_total"],
            "km_open": s["km_open"],
            "km_total": s["km_total"],
            "percent_open": s["pct_open"],
            "next_opening": s["opening"] or None,
            "opening_info": s["info"] or None,
            "trails": s["trails"],
            "green_blue_percent": s["vb"],
            "travel_min": s["travel"],
            "snow_72h_cm": weather.get("snow72"),
            "snow_tomorrow_cm": weather.get("snow_tomorrow"),
            "weather": weather.get("label"),
            "temperature_max": weather.get("tmax"),
            "score": s["score"],
            "url": s["url"],
        }
