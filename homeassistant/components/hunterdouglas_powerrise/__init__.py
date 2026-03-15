"""The Hunter Douglas PowerRise integration."""

from __future__ import annotations

import logging

from aiopowerrise.exceptions import ConnectionError as PowerRiseConnectionError
from aiopowerrise.hub import Hub

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, MANUFACTURER
from .coordinator import PowerRiseDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.COVER]

type PowerRiseConfigEntry = ConfigEntry[PowerRiseDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: PowerRiseConfigEntry) -> bool:
    """Set up Hunter Douglas PowerRise from a config entry."""
    host: str = entry.data[CONF_HOST]

    hub = Hub(host)
    try:
        await hub.connect()
        house = await hub.get_data()
    except (PowerRiseConnectionError, TimeoutError, OSError) as err:
        await hub.close()
        raise ConfigEntryNotReady(
            f"Connection error to PowerRise hub {host}: {err}"
        ) from err

    # Register the hub as a device
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, host)},
        manufacturer=MANUFACTURER,
        name=house.name or "PowerRise Hub",
        model="PowerRise Platinum",
        sw_version=str(house.bridge.firmware_version)
        if house.bridge.firmware_version
        else None,
    )

    coordinator = PowerRiseDataUpdateCoordinator(hass, entry, hub)

    await coordinator.async_config_entry_first_refresh()

    # Start push listener AFTER the first refresh so hub.house is populated.
    # The listener feeds real-time shade position updates directly into the
    # coordinator, avoiding the need for a new get_data() on every remote move.
    coordinator.start_push_listener()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: PowerRiseConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: PowerRiseDataUpdateCoordinator = entry.runtime_data
        await coordinator.async_shutdown()
    return unload_ok
