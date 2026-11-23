"""Integration tests."""
import re

from homeassistant.core import HomeAssistant
from homeassistant import config_entries
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from custom_components.magic_pass.const import DOMAIN, EVENT_STATION_OPENED

from .fixtures import MARKERS, OSRM, meteo, opening_page, region_page


def mock_all(aioclient_mock, page):
    aioclient_mock.clear_requests()
    aioclient_mock.get(re.compile(r"https://www\.magicpass\.ch/fr/stations/opening\?states%5B%5D=10"), text=region_page("10"))
    aioclient_mock.get(re.compile(r"https://www\.magicpass\.ch/fr/stations/opening\?states%5B%5D=8"), text=region_page("8"))
    aioclient_mock.get("https://www.magicpass.ch/fr/stations/opening", text=page)
    aioclient_mock.post(re.compile(r"https://map\.magicpass\.ch/markers.*"), json=MARKERS)
    aioclient_mock.get(re.compile(r"https://router\.project-osrm\.org/.*"), json=OSRM)
    aioclient_mock.get(re.compile(r"https://api\.open-meteo\.com/.*"), json=meteo(3))


async def test_config_flow(hass: HomeAssistant, aioclient_mock) -> None:
    mock_all(aioclient_mock, opening_page())
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == "form"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"location": {"latitude": 46.62, "longitude": 7.06}, "max_travel": 120, "scan_interval": 30},
    )
    assert result["type"] == "create_entry"
    assert result["data"]["latitude"] == 46.62
    await hass.async_block_till_done()


async def test_setup_sensors_ws_and_event(hass: HomeAssistant, aioclient_mock, hass_ws_client) -> None:
    mock_all(aioclient_mock, opening_page())
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"latitude": 46.62, "longitude": 7.06, "max_travel": 120, "scan_interval": 30},
        options={"tracked_stations": ["charmey-14"]},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    states = {s.entity_id: s for s in hass.states.async_all("sensor")}
    open_resorts = next(s for e, s in states.items() if e.endswith("open_resorts"))
    assert open_resorts.state == "1"
    best = next(s for e, s in states.items() if e.endswith("best_resort"))
    assert best.state == "Villars-Gryon"
    assert best.attributes["travel_min"] == 54
    charmey = next(s for e, s in states.items() if e.endswith("charmey"))
    assert charmey.state == "closed"
    assert charmey.attributes["travel_min"] == 17
    assert charmey.attributes["region"] == "Fribourg"
    assert charmey.attributes["next_opening"]
    assert charmey.attributes["green_blue_percent"] == 50
    assert charmey.attributes["snow_72h_cm"] > 0

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "magic_pass/subscribe"})
    msg = await client.receive_json()
    assert msg["success"]
    msg = await client.receive_json()
    data = msg["event"]
    assert data["count"] == 3 and data["open"] == 1
    assert [s["name"] for s in data["stations"]][0] == "Charmey"

    events = async_capture_events(hass, EVENT_STATION_OPENED)
    mock_all(aioclient_mock, opening_page("Ouvert", "3/7", "12/29.2"))
    coordinator = entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert len(events) == 1 and events[0].data["name"] == "Charmey"
    assert hass.states.get(charmey.entity_id).state == "open"
    update = await client.receive_json()
    assert update["event"]["open"] == 2

    await client.send_json({"id": 2, "type": "magic_pass/refresh"})
    while True:
        msg = await client.receive_json()
        if msg["id"] == 2 and msg["type"] == "result":
            assert msg["success"]
            break

    assert await hass.config_entries.async_unload(entry.entry_id)
