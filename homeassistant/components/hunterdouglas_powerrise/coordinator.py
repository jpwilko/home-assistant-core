"""DataUpdateCoordinator for Hunter Douglas PowerRise."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import timedelta
import logging
from typing import Any

from aiopowerrise.exceptions import (
    ConnectionError as PowerRiseConnectionError,
    PowerRiseError,
)
from aiopowerrise.hub import Hub
from aiopowerrise.models import House, Shade

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# How long to wait between reconnect attempts
_RECONNECT_DELAY = 10.0
# Max reconnect attempts before giving up (entry reload)
_MAX_RECONNECT_ATTEMPTS = 5


class PowerRiseDataUpdateCoordinator(DataUpdateCoordinator[House]):
    """DataUpdateCoordinator for a PowerRise hub.

    Uses the hub's push listener for instant real-time updates when shades
    are moved by a remote or app outside of Home Assistant.  Periodic polling
    via ``get_data()`` is kept as a fallback to re-sync the full state.
    Automatic reconnection is triggered when the reader loop detects the
    connection has been lost.
    """

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        hub: Hub,
    ) -> None:
        """Initialize DataUpdateCoordinator for a PowerRise hub."""
        self.hub = hub
        self._reconnect_task: asyncio.Task[None] | None = None
        self._reconnect_attempts = 0
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN} {hub.host}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    def start_push_listener(self) -> None:
        """Register the HA update callback and wire the hub's line callback.

        The reader loop is already running (started inside transport.connect()).
        hub.start_listening() calls transport.set_line_callback(hub._on_line)
        so unsolicited lines reach the hub's listener dispatcher.
        We also register a disconnect callback so we can auto-reconnect.
        """
        self.hub.add_listener(self._on_hub_event)
        self.hub.start_listening()
        self.hub.set_disconnect_callback(self._on_hub_disconnected)
        _LOGGER.debug("Push listener registered for %s", self.hub.host)

    def _on_hub_disconnected(self) -> None:
        """Called by the transport reader loop when the connection is unexpectedly lost.

        This is called from inside the reader loop asyncio.Task, so we must
        schedule the reconnect coroutine rather than awaiting it directly.
        """
        _LOGGER.warning(
            "Lost connection to PowerRise hub %s — scheduling reconnect",
            self.hub.host,
        )
        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = self.hass.async_create_task(
                self._async_reconnect_loop(),
                name=f"powerrise_reconnect_{self.hub.host}",
            )

    async def _async_reconnect_loop(self) -> None:
        """Attempt to reconnect to the hub with exponential back-off."""
        self._reconnect_attempts = 0
        while self._reconnect_attempts < _MAX_RECONNECT_ATTEMPTS:
            self._reconnect_attempts += 1
            delay = _RECONNECT_DELAY * self._reconnect_attempts
            _LOGGER.info(
                "Reconnect attempt %d/%d for %s in %.0fs",
                self._reconnect_attempts,
                _MAX_RECONNECT_ATTEMPTS,
                self.hub.host,
                delay,
            )
            await asyncio.sleep(delay)
            try:
                await self.hub.connect()
                # Re-wire the line callback and keepalive after reconnect
                self.hub.start_listening()
                self.hub.set_disconnect_callback(self._on_hub_disconnected)
                # Force a full data refresh so coordinator state is consistent
                await self.async_refresh()
                _LOGGER.info(
                    "Reconnected to PowerRise hub %s after %d attempt(s)",
                    self.hub.host,
                    self._reconnect_attempts,
                )
                self._reconnect_attempts = 0
            except Exception:  # noqa: BLE001
                _LOGGER.warning(
                    "Reconnect attempt %d failed for %s",
                    self._reconnect_attempts,
                    self.hub.host,
                )
            else:
                return

        _LOGGER.error(
            "Failed to reconnect to PowerRise hub %s after %d attempts — reloading entry",
            self.hub.host,
            _MAX_RECONNECT_ATTEMPTS,
        )
        self.hass.async_create_task(
            self.hass.config_entries.async_reload(self.config_entry.entry_id)
        )

    async def async_shutdown(self) -> None:
        """Cancel any in-progress reconnect task and close the hub."""
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task
        self._reconnect_task = None
        await self.hub.close()

    @callback
    def _on_hub_event(self, event_type: str, data: Any) -> None:
        """Handle a push event from the hub listener.

        The hub calls this from its ``_on_line`` handler whenever an
        unsolicited ``$cp`` (shade position) or ``$cr`` (room) line arrives.
        We update the coordinator data in-place and notify all subscribers so
        HA entities update immediately without waiting for the next poll.
        """
        if event_type == "shade" and isinstance(data, Shade):
            house = self.data
            if house is not None and data.id in house.shades:
                # Merge the updated shade into our current House snapshot
                house.shades[data.id] = data
                _LOGGER.debug(
                    "Push update: shade %d → %d%%", data.id, data.position_percent
                )
                self.async_set_updated_data(house)

    async def _async_update_data(self) -> House:
        """Fetch a full data snapshot from the hub (periodic fallback poll)."""
        if not self.hub.connected:
            # If disconnected, don't raise UpdateFailed — the reconnect loop will
            # call async_refresh() once the connection is restored.
            if self.data is not None:
                return self.data
            raise UpdateFailed(f"Not connected to PowerRise hub {self.hub.host}")
        try:
            house = await self.hub.get_data()
        except PowerRiseConnectionError as err:
            raise UpdateFailed(
                f"Connection error to PowerRise hub {self.hub.host}: {err}"
            ) from err
        except PowerRiseError as err:
            raise UpdateFailed(
                f"Error fetching data from PowerRise hub {self.hub.host}: {err}"
            ) from err

        if house is None:
            raise UpdateFailed("No data returned from PowerRise hub")

        return house
