"""Support for Hunter Douglas PowerRise shades."""

from __future__ import annotations

import logging
from typing import Any

from aiopowerrise.models import House, Room, Shade

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PowerRiseConfigEntry
from .coordinator import PowerRiseDataUpdateCoordinator
from .entity import PowerRiseEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PowerRiseConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Hunter Douglas PowerRise cover entities."""
    coordinator: PowerRiseDataUpdateCoordinator = entry.runtime_data
    house: House = coordinator.data

    entities: list[PowerRiseCover] = []
    for shade in house.shades.values():
        room = house.rooms.get(shade.room_id)
        room_name = room.name if room else ""
        entities.append(
            PowerRiseCover(
                coordinator=coordinator,
                shade=shade,
                room_name=room_name,
                room=room,
            )
        )

    async_add_entities(entities)


class PowerRiseCover(PowerRiseEntity, CoverEntity):
    """Representation of a Hunter Douglas PowerRise shade."""

    _attr_device_class = CoverDeviceClass.SHADE
    _attr_translation_key = "shade"

    def __init__(
        self,
        coordinator: PowerRiseDataUpdateCoordinator,
        shade: Shade,
        room_name: str,
        room: Room | None,
    ) -> None:
        """Initialize the shade cover."""
        super().__init__(coordinator, shade, room_name)
        self._room = room

        # Determine supported features based on shade capabilities
        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
        )

        if shade.supports_tilt:
            self._attr_supported_features |= (
                CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
                | CoverEntityFeature.SET_TILT_POSITION
            )

    def _get_shade(self) -> Shade | None:
        """Get the current shade data from the coordinator."""
        house: House = self.coordinator.data
        return house.shades.get(self._shade.id)

    @property
    def assumed_state(self) -> bool:
        """Return True since PowerRise shades use assumed state.

        The hub may not always reflect real-time positions accurately,
        especially for battery-powered shades.
        """
        return True

    @property
    def current_cover_position(self) -> int | None:
        """Return the current position of the shade.

        HA uses 0=closed, 100=open which matches the library.
        """
        shade = self._get_shade()
        if shade is None:
            return None
        return shade.position_percent

    @property
    def current_cover_tilt_position(self) -> int | None:
        """Return the current tilt position of the shade."""
        shade = self._get_shade()
        if shade is None or not shade.supports_tilt:
            return None
        return shade.tilt_percent

    @property
    def is_closed(self) -> bool | None:
        """Return if the shade is closed."""
        shade = self._get_shade()
        if shade is None:
            return None
        return shade.is_closed

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the shade."""
        shade = self._get_shade()
        await self.coordinator.hub.shades.open(self._shade.id, shade=shade)
        self.coordinator.async_set_updated_data(self.coordinator.data)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the shade."""
        shade = self._get_shade()
        await self.coordinator.hub.shades.close(self._shade.id, shade=shade)
        self.coordinator.async_set_updated_data(self.coordinator.data)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the shade."""
        await self.coordinator.hub.shades.stop(self._shade.id)
        await self.coordinator.async_request_refresh()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the shade to a specific position."""
        position: int = kwargs[ATTR_POSITION]
        shade = self._get_shade()
        await self.coordinator.hub.shades.move(self._shade.id, position, shade=shade)
        self.coordinator.async_set_updated_data(self.coordinator.data)

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the shade tilt."""
        shade = self._get_shade()
        if shade is None:
            return
        await self.coordinator.hub.shades.tilt(
            self._shade.id, 100, shade.supports_tilt_reverse, shade=shade
        )
        self.coordinator.async_set_updated_data(self.coordinator.data)

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the shade tilt."""
        shade = self._get_shade()
        if shade is None:
            return
        await self.coordinator.hub.shades.tilt(
            self._shade.id, 0, shade.supports_tilt_reverse, shade=shade
        )
        self.coordinator.async_set_updated_data(self.coordinator.data)

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Set the shade tilt to a specific position."""
        shade = self._get_shade()
        if shade is None:
            return
        tilt_position: int = kwargs[ATTR_TILT_POSITION]
        await self.coordinator.hub.shades.tilt(
            self._shade.id, tilt_position, shade.supports_tilt_reverse, shade=shade
        )
        self.coordinator.async_set_updated_data(self.coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
