"""Config flow for the Hunter Douglas PowerRise integration."""

from __future__ import annotations

import logging
from typing import Any

from aiopowerrise.discovery import discover_hub
from aiopowerrise.hub import Hub
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST

from .const import CONF_USE_DISCOVERY, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)

STEP_RECONFIGURE_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USE_DISCOVERY, default=False): bool,
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
        mac_address = hub.mac_address
    finally:
        await hub.close()

    return {
        "title": name,
        "firmware": firmware,
        "host": host,
        "mac_address": mac_address,
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
            return await self._async_validate_and_create(
                user_input[CONF_HOST], use_discovery=False
            )

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
            return await self._async_validate_and_create(
                self.discovered_ip, use_discovery=True
            )

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
            return await self._async_validate_and_create(
                user_input[CONF_HOST], use_discovery=False, errors=errors
            )

        return self.async_show_form(
            step_id="manual",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host: str = user_input[CONF_HOST]
            use_discovery: bool = user_input[CONF_USE_DISCOVERY]
            try:
                # Validate connectivity; return value not needed here.
                await _async_try_connect(host)
            except OSError, TimeoutError:
                _LOGGER.debug("Could not connect to hub at %s", host)
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_HOST: host,
                        CONF_USE_DISCOVERY: use_discovery,
                    },
                )

        current_host = entry.data.get(CONF_HOST, "")
        current_use_discovery = entry.data.get(CONF_USE_DISCOVERY, False)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=current_host): str,
                    vol.Required(
                        CONF_USE_DISCOVERY, default=current_use_discovery
                    ): bool,
                }
            ),
            errors=errors,
        )

    async def _async_validate_and_create(
        self,
        host: str,
        *,
        use_discovery: bool = False,
        errors: dict[str, str] | None = None,
    ) -> ConfigFlowResult:
        """Validate connection and create the config entry."""
        if errors is None:
            errors = {}

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

        mac = info["mac_address"] or host
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: host, CONF_USE_DISCOVERY: use_discovery}
        )

        return self.async_create_entry(
            title=info["title"],
            data={CONF_HOST: host, CONF_USE_DISCOVERY: use_discovery},
        )
