"""Diagnostics support for fibaro integration."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pyfibaro.fibaro_device import DeviceModel

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_UNIQUE_ID, CONF_URL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from . import FibaroController
from .const import DOMAIN

TO_REDACT = {CONF_PASSWORD, CONF_USERNAME, CONF_URL, CONF_UNIQUE_ID, "title"}


def _create_diagnostics_data(
    config_entry: ConfigEntry, controller: FibaroController, devices: list[DeviceModel]
) -> dict[str, Any]:
    """Combine diagnostics information and redact sensitive information."""
    diagnostics_data = {
        "config": config_entry.as_dict(),
        "software_version": controller.hub_software_version,
        "fibaro_devices": [d.raw_data for d in devices],
    }

    return async_redact_data(diagnostics_data, TO_REDACT)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> Mapping[str, Any]:
    """Return diagnostics for a config entry."""
    controller: FibaroController = hass.data[DOMAIN][config_entry.entry_id]
    devices = controller.read_devices()

    return _create_diagnostics_data(config_entry, controller, devices)


async def async_get_device_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry, device: DeviceEntry
) -> Mapping[str, Any]:
    """Return diagnostics for a device."""
    controller: FibaroController = hass.data[DOMAIN][config_entry.entry_id]
    devices = controller.read_devices()

    filtered_devices = []

    ha_device_id = next(iter(device.identifiers))[1]
    if ha_device_id == controller.hub_serial:
        # special case main device representing the fibaro hub
        for fibaro_device in devices:
            if fibaro_device.fibaro_id == 1:
                filtered_devices.append(fibaro_device)
    else:
        # normal devices are represented by a parent structure and children's
        for fibaro_device in devices:
            if ha_device_id in (
                fibaro_device.fibaro_id,
                fibaro_device.parent_fibaro_id,
            ):
                filtered_devices.append(fibaro_device)

    return _create_diagnostics_data(config_entry, controller, filtered_devices)
