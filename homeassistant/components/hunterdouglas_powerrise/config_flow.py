"""Config flow for the Hunter Douglas PowerRise integration."""

from __future__ import annotations

import logging
from typing import Any

from aiopowerrise.discovery import discover_hub
from aiopowerrise.hub import Hub
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)


async def _async_try_connect(host: str) -> dict[str, Any]:
    """Validate we can connect to the hub and return info.

    Raises an exception if the connection fails.
    """

    hub = Hub(host)
    try:
        await hub.connect()
        house = await hub.get_data()
        name = house.name or "PowerRise Hub"
        firmware = house.bridge.firmware_version
    finally:
        await hub.close()

    return {
        "title": name,
        "firmware": firmware,
        "host": host,
    }


async def _async_discover_hub() -> str | None:
    """Discover a PowerRise hub on the network."""

    return await discover_hub(timeout=5.0)


class PowerRiseConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hunter Douglas PowerRise."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.discovered_ip: str | None = None
        self.discovered_name: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step.

        Attempt auto-discovery first; if a hub is found, offer confirmation.
        Otherwise, show a form for manual IP entry.
        """
        if user_input is not None:
            return await self._async_validate_and_create(user_input[CONF_HOST])

        # Try auto-discovery
        discovered_ip = await _async_discover_hub()
        if discovered_ip:
            self.discovered_ip = discovered_ip
            return await self.async_step_discovery_confirm()

        # No hub found; show manual entry form
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
        )

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle confirmation of a discovered hub."""

        if user_input is not None:
            assert self.discovered_ip is not None
            return await self._async_validate_and_create(self.discovered_ip)

        # Try to get the hub name for the description
        assert self.discovered_ip is not None
        try:
            info = await _async_try_connect(self.discovered_ip)
            self.discovered_name = info["title"]
        except OSError, TimeoutError:
            _LOGGER.debug(
                "Could not connect to discovered hub at %s", self.discovered_ip
            )
            # Fall back to manual entry if we can't connect to the discovered hub
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors={"base": "cannot_connect"},
            )

        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                "host": self.discovered_ip,
                "name": self.discovered_name or "PowerRise Hub",
            },
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual IP entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            return await self._async_validate_and_create(user_input[CONF_HOST], errors)

        return self.async_show_form(
            step_id="manual",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def _async_validate_and_create(
        self, host: str, errors: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Validate connection and create the config entry."""
        if errors is None:
            errors = {}

        # Prevent duplicate entries for the same host
        self._async_abort_entries_match({CONF_HOST: host})

        try:
            info = await _async_try_connect(host)
        except OSError, TimeoutError:
            _LOGGER.exception("Error connecting to PowerRise hub at %s", host)
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors=errors,
            )

        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        return self.async_create_entry(
            title=info["title"],
            data={CONF_HOST: host},
        )
