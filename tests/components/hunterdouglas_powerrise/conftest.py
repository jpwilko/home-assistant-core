"""Fixtures for Hunter Douglas PowerRise tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from aiopowerrise.models import Bridge, House, Room, Shade
import pytest

from homeassistant.components.hunterdouglas_powerrise.const import DOMAIN
from homeassistant.const import CONF_HOST

from tests.common import MockConfigEntry

MOCK_HOST = "192.168.1.100"
MOCK_HOUSE_NAME = "My Home"
MOCK_FIRMWARE = 18


def _create_mock_house() -> House:
    """Create a mock House with rooms and shades."""
    house = House()
    house.name = MOCK_HOUSE_NAME
    house.bridge = Bridge(firmware_version=MOCK_FIRMWARE)

    # Room 1: Standard shade (Duette)
    room1 = Room(id=1, name="Living Room", brand_index=1)
    # Room 2: Tilt shade (Silhouette)
    room2 = Room(id=2, name="Bedroom", brand_index=10)

    # Standard shade
    shade1 = Shade(
        id=1,
        name="Living Room Shade",
        room_id=1,
        position=128,  # ~50% open
        supports_tilt=False,
        supports_tilt_reverse=False,
    )
    # Tilt-capable shade
    shade2 = Shade(
        id=2,
        name="Bedroom Shade",
        room_id=2,
        position=0,
        tilt_position=128,
        supports_tilt=True,
        supports_tilt_reverse=False,
    )

    room1.shades = [1]
    room2.shades = [2]

    house.rooms = {1: room1, 2: room2}
    house.shades = {1: shade1, 2: shade2}
    house.scenes = {}

    return house


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=MOCK_HOUSE_NAME,
        data={CONF_HOST: MOCK_HOST},
        unique_id=MOCK_HOST,
    )


@pytest.fixture
def mock_hub() -> Generator[MagicMock]:
    """Create a mock Hub."""
    mock_house = _create_mock_house()

    with patch(
        "homeassistant.components.hunterdouglas_powerrise.Hub",
        autospec=True,
    ) as mock_hub_class:
        hub_instance = mock_hub_class.return_value
        hub_instance.host = MOCK_HOST
        hub_instance.port = 522
        hub_instance.connected = True
        hub_instance.name = MOCK_HOUSE_NAME
        hub_instance.firmware_version = MOCK_FIRMWARE
        hub_instance.house = mock_house

        hub_instance.connect = AsyncMock()
        hub_instance.close = AsyncMock()
        hub_instance.get_data = AsyncMock(return_value=mock_house)
        hub_instance.ping = AsyncMock(return_value=True)
        hub_instance.start_listening = MagicMock()
        hub_instance.stop_listening = MagicMock()
        hub_instance.add_listener = MagicMock(return_value=MagicMock())

        # Mock shade operations
        hub_instance.shades = MagicMock()
        hub_instance.shades.move = AsyncMock()
        hub_instance.shades.open = AsyncMock()
        hub_instance.shades.close = AsyncMock()
        hub_instance.shades.stop = AsyncMock()
        hub_instance.shades.tilt = AsyncMock()

        # Mock scene operations
        hub_instance.scenes = MagicMock()
        hub_instance.scenes.activate = AsyncMock()

        yield hub_instance


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.hunterdouglas_powerrise.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup
