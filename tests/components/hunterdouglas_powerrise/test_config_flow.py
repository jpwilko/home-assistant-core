"""Test the Hunter Douglas PowerRise config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant import config_entries
from homeassistant.components.hunterdouglas_powerrise.const import DOMAIN
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


@pytest.fixture
def mock_discover_hub():
    """Mock the discover_hub function."""
    with patch(
        "homeassistant.components.hunterdouglas_powerrise.config_flow._async_discover_hub",
    ) as mock_discover:
        yield mock_discover


@pytest.fixture
def mock_try_connect(mock_hub: MagicMock):
    """Mock the _async_try_connect function."""
    with patch(
        "homeassistant.components.hunterdouglas_powerrise.config_flow._async_try_connect",
        return_value={
            "title": "My Home",
            "firmware": 18,
            "host": "192.168.1.100",
        },
    ) as mock_connect:
        yield mock_connect


async def test_user_form_no_discovery(
    hass: HomeAssistant,
    mock_discover_hub: AsyncMock,
    mock_try_connect: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test manual entry when no hub is discovered."""
    mock_discover_hub.return_value = None

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.1.100"},
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "My Home"
    assert result2["data"] == {CONF_HOST: "192.168.1.100"}


async def test_user_form_discovery(
    hass: HomeAssistant,
    mock_discover_hub: AsyncMock,
    mock_try_connect: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test auto-discovery flow."""
    mock_discover_hub.return_value = "192.168.1.100"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    # Should go to discovery_confirm step
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "My Home"
    assert result2["data"] == {CONF_HOST: "192.168.1.100"}


async def test_user_form_cannot_connect(
    hass: HomeAssistant,
    mock_discover_hub: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test we handle connection errors."""
    mock_discover_hub.return_value = None

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "homeassistant.components.hunterdouglas_powerrise.config_flow._async_try_connect",
        side_effect=OSError("Connection refused"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.1.100"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_user_form_already_configured(
    hass: HomeAssistant,
    mock_discover_hub: AsyncMock,
    mock_try_connect: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test we abort if already configured."""
    mock_discover_hub.return_value = None
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.1.100"},
    )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_discovery_cannot_connect_falls_back(
    hass: HomeAssistant,
    mock_discover_hub: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that discovery falls back to manual entry when connection fails."""
    mock_discover_hub.return_value = "192.168.1.100"

    with patch(
        "homeassistant.components.hunterdouglas_powerrise.config_flow._async_try_connect",
        side_effect=OSError("Connection refused"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    # Should fall back to manual entry form
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}
