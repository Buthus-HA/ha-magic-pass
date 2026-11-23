"""The Magic Pass integration."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CARD_URL, DOMAIN, VERSION
from .coordinator import MagicPassCoordinator

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type MagicPassConfigEntry = ConfigEntry[MagicPassCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the dashboard card and the websocket API once."""
    card = Path(__file__).parent / "frontend" / "magic-pass-card.js"
    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(card), False)])
    add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_refresh)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MagicPassConfigEntry) -> bool:
    """Set up Magic Pass from a config entry."""
    coordinator = MagicPassCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MagicPassConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: MagicPassConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _coordinator(hass: HomeAssistant, entry_id: str | None) -> MagicPassCoordinator | None:
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        if entry_id in (None, entry.entry_id):
            return entry.runtime_data
    return None


@websocket_api.websocket_command(
    {vol.Required("type"): "magic_pass/subscribe", vol.Optional("entry_id"): str}
)
@callback
def ws_subscribe(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Send the full resort table now and after every update."""
    coordinator = _coordinator(hass, msg.get("entry_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "No Magic Pass entry is loaded")
        return

    @callback
    def _send() -> None:
        connection.send_message(websocket_api.event_message(msg["id"], coordinator.data))

    connection.subscriptions[msg["id"]] = coordinator.async_add_listener(_send)
    connection.send_result(msg["id"])
    _send()


@websocket_api.websocket_command(
    {vol.Required("type"): "magic_pass/refresh", vol.Optional("entry_id"): str}
)
@websocket_api.async_response
async def ws_refresh(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Refresh the data now."""
    coordinator = _coordinator(hass, msg.get("entry_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "No Magic Pass entry is loaded")
        return
    await coordinator.async_refresh()
    connection.send_result(msg["id"])
