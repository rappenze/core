"""Config flow for Fibaro integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from pyfibaro.fibaro_client import (
    FibaroAuthenticationFailed,
    FibaroClient,
    FibaroConnectFailed,
)
from requests.exceptions import HTTPError
from slugify import slugify
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from . import connect_fibaro_client
from .const import CONF_IMPORT_PLUGINS, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    info, _ = await hass.async_add_executor_job(connect_fibaro_client, data)

    _LOGGER.debug(
        "Successfully connected to fibaro home center %s with name %s",
        info.serial_number,
        info.hc_name,
    )
    return {
        "serial_number": slugify(info.serial_number),
        "name": info.hc_name,
    }


def _get_info(url: str) -> dict[str, Any]:
    info = FibaroClient(url).read_info()
    return {
        "serial_number": slugify(info.serial_number),
        "name": info.hc_name,
    }


def _normalize_url(url: str) -> str:
    """Try to fix errors in the entered url.

    We know that the url should be in the format http://<HOST>/api/
    """
    if url.endswith("/api"):
        return f"{url}/"
    if not url.endswith("/api/"):
        return f"{url}api/" if url.endswith("/") else f"{url}/api/"
    return url


class FibaroConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fibaro."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the Daikin config flow."""
        self.url: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                user_input[CONF_URL] = _normalize_url(user_input[CONF_URL])
                info = await _validate_input(self.hass, user_input)
            except FibaroConnectFailed:
                errors["base"] = "cannot_connect"
            except FibaroAuthenticationFailed:
                errors["base"] = "invalid_auth"
            else:
                await self.async_set_unique_id(info["serial_number"])
                self._abort_if_unique_id_configured(updates=user_input)
                return self.async_create_entry(title=info["name"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL, default=self.url): str,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_IMPORT_PLUGINS, default=False): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by reauthentication."""
        errors = {}

        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            new_data = reauth_entry.data | user_input
            try:
                await _validate_input(self.hass, new_data)
            except FibaroConnectFailed:
                errors["base"] = "cannot_connect"
            except FibaroAuthenticationFailed:
                errors["base"] = "invalid_auth"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry, data_updates=user_input
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={
                CONF_USERNAME: reauth_entry.data[CONF_USERNAME],
                CONF_NAME: reauth_entry.title,
            },
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery for fibaro hub."""
        serial_number = slugify(discovery_info.name.split(".", 1)[0])
        url = _normalize_url(f"http://{discovery_info.ip_address}")

        await self.async_set_unique_id(serial_number)
        self._abort_if_unique_id_configured(updates={CONF_URL: url})

        # Double check that we are discovering a Fibaro Hub by reading the serial number
        # from the API again so we do not rely only on the discovered name
        try:
            info = await self.hass.async_add_executor_job(_get_info, url)
            if info["serial_number"] == serial_number:
                self.url = url
                self.context.update({"title_placeholders": {CONF_NAME: info["name"]}})
                return await self.async_step_user()
        except HTTPError:
            _LOGGER.debug(
                "Zeroconf for fibaro detected another device by name %s", serial_number
            )

        return self.async_abort(reason="no_fibaro_hub")
