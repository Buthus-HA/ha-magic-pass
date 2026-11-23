"""Config flow for Magic Pass."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_LATITUDE,
    CONF_LOCATION,
    CONF_LONGITUDE,
    CONF_MAX_TRAVEL,
    CONF_SCAN_INTERVAL,
    CONF_TRACKED,
    DEFAULT_MAX_TRAVEL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)


def _schema(lat: float, lon: float, max_travel: int, interval: int) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_LOCATION, default={"latitude": lat, "longitude": lon}): selector.LocationSelector(
                selector.LocationSelectorConfig(radius=False)
            ),
            vol.Required(CONF_MAX_TRAVEL, default=max_travel): selector.NumberSelector(
                selector.NumberSelectorConfig(min=15, max=360, step=5, unit_of_measurement="min", mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_SCAN_INTERVAL, default=interval): selector.NumberSelector(
                selector.NumberSelectorConfig(min=MIN_SCAN_INTERVAL, max=240, step=5, unit_of_measurement="min", mode=selector.NumberSelectorMode.BOX)
            ),
        }
    )


def _flatten(user_input: dict[str, Any]) -> dict[str, Any]:
    location = user_input.pop(CONF_LOCATION)
    return {
        **user_input,
        CONF_LATITUDE: location["latitude"],
        CONF_LONGITUDE: location["longitude"],
        CONF_MAX_TRAVEL: int(user_input[CONF_MAX_TRAVEL]),
        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
    }


class MagicPassConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the setup."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """First and only step: starting point and preferences."""
        if user_input is not None:
            data = _flatten(user_input)
            await self.async_set_unique_id(f"{data[CONF_LATITUDE]:.3f},{data[CONF_LONGITUDE]:.3f}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Magic Pass", data=data)
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(
                self.hass.config.latitude, self.hass.config.longitude, DEFAULT_MAX_TRAVEL, DEFAULT_SCAN_INTERVAL
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Options."""
        return MagicPassOptionsFlow()


class MagicPassOptionsFlow(OptionsFlow):
    """Change the starting point, preferences and resorts exposed as entities."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage options."""
        entry = self.config_entry
        get = lambda key, default: entry.options.get(key, entry.data.get(key, default))  # noqa: E731
        if user_input is not None:
            tracked = user_input.pop(CONF_TRACKED, [])
            data = _flatten(user_input)
            data[CONF_TRACKED] = tracked
            return self.async_create_entry(data=data)

        coordinator = getattr(entry, "runtime_data", None)
        stations = (coordinator.data or {}).get("stations", []) if coordinator else []
        choices = sorted(
            ({"value": s["slug"], "label": f"{s['name']}{' (' + s['region'] + ')' if s['region'] else ''}"} for s in stations),
            key=lambda c: c["label"].lower(),
        )
        schema = _schema(
            get(CONF_LATITUDE, self.hass.config.latitude),
            get(CONF_LONGITUDE, self.hass.config.longitude),
            get(CONF_MAX_TRAVEL, DEFAULT_MAX_TRAVEL),
            get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ).extend(
            {
                vol.Optional(CONF_TRACKED, default=get(CONF_TRACKED, [])): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=choices, multiple=True, mode=selector.SelectSelectorMode.DROPDOWN)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
