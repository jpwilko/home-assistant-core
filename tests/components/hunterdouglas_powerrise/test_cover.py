"""Test the Hunter Douglas PowerRise cover platform."""

from __future__ import annotations

from unittest.mock import ANY, MagicMock

from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_CLOSE_COVER_TILT,
    SERVICE_OPEN_COVER,
    SERVICE_OPEN_COVER_TILT,
    SERVICE_SET_COVER_POSITION,
    SERVICE_SET_COVER_TILT_POSITION,
    SERVICE_STOP_COVER,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_cover_setup(
    hass: HomeAssistant,
    mock_hub: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that covers are created for each shade."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Check that cover entities were created
    state1 = hass.states.get("cover.living_room_shade_shade")
    state2 = hass.states.get("cover.bedroom_shade_shade")

    assert state1 is not None
    assert state2 is not None


async def test_cover_position(
    hass: HomeAssistant,
    mock_hub: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test cover position reporting."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("cover.living_room_shade_shade")
    assert state is not None
    # Shade 1 has position 128 (~50%)
    position = state.attributes.get(ATTR_CURRENT_POSITION)
    assert position is not None
    assert position == 50


async def test_cover_open(
    hass: HomeAssistant,
    mock_hub: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test opening a cover."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER,
        {ATTR_ENTITY_ID: "cover.living_room_shade_shade"},
        blocking=True,
    )

    mock_hub.shades.open.assert_called_once_with(1, shade=ANY)


async def test_cover_close(
    hass: HomeAssistant,
    mock_hub: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test closing a cover."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_CLOSE_COVER,
        {ATTR_ENTITY_ID: "cover.living_room_shade_shade"},
        blocking=True,
    )

    mock_hub.shades.close.assert_called_once_with(1, shade=ANY)


async def test_cover_stop(
    hass: HomeAssistant,
    mock_hub: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test stopping a cover."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_STOP_COVER,
        {ATTR_ENTITY_ID: "cover.living_room_shade_shade"},
        blocking=True,
    )

    mock_hub.shades.stop.assert_called_once_with(1)


async def test_cover_set_position(
    hass: HomeAssistant,
    mock_hub: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting cover position."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: "cover.living_room_shade_shade", ATTR_POSITION: 75},
        blocking=True,
    )

    mock_hub.shades.move.assert_called_once_with(1, 75, shade=ANY)


async def test_cover_tilt(
    hass: HomeAssistant,
    mock_hub: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test tilt-capable cover."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("cover.bedroom_shade_shade")
    assert state is not None
    # Shade 2 supports tilt
    tilt = state.attributes.get(ATTR_CURRENT_TILT_POSITION)
    assert tilt is not None


async def test_cover_set_tilt_position(
    hass: HomeAssistant,
    mock_hub: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting cover tilt position."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_SET_COVER_TILT_POSITION,
        {ATTR_ENTITY_ID: "cover.bedroom_shade_shade", ATTR_TILT_POSITION: 50},
        blocking=True,
    )

    mock_hub.shades.tilt.assert_called_once_with(2, 50, False, shade=ANY)


async def test_cover_open_tilt(
    hass: HomeAssistant,
    mock_hub: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test opening cover tilt."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.bedroom_shade_shade"},
        blocking=True,
    )

    mock_hub.shades.tilt.assert_called_once_with(2, 100, False, shade=ANY)


async def test_cover_close_tilt(
    hass: HomeAssistant,
    mock_hub: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test closing cover tilt."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_CLOSE_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.bedroom_shade_shade"},
        blocking=True,
    )

    mock_hub.shades.tilt.assert_called_once_with(2, 0, False, shade=ANY)


async def test_unload_entry(
    hass: HomeAssistant,
    mock_hub: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test unloading the config entry."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    mock_hub.close.assert_called()
