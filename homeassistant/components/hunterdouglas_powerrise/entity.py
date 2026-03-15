"""Base entity for Hunter Douglas PowerRise."""

from __future__ import annotations

from aiopowerrise.models import Shade

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import PowerRiseDataUpdateCoordinator


class PowerRiseEntity(CoordinatorEntity[PowerRiseDataUpdateCoordinator]):
    """Base class for Hunter Douglas PowerRise entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PowerRiseDataUpdateCoordinator,
        shade: Shade,
        room_name: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._shade = shade
        self._room_name = room_name
        self._attr_unique_id = f"{coordinator.hub.host}_{shade.id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.hub.host}_{shade.id}")},
            name=shade.name,
            manufacturer=MANUFACTURER,
            model=self._get_shade_model(shade),
            suggested_area=room_name,
            via_device=(DOMAIN, coordinator.hub.host),
        )

    @staticmethod
    def _get_shade_model(shade: Shade) -> str:
        """Determine shade model string from room brand info."""
        return "PowerRise Platinum Shade"
