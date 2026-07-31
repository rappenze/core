"""Test init methods."""

from unittest.mock import Mock, patch

from homeassistant.components.fibaro import DOMAIN
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .conftest import TEST_SERIALNUMBER, init_integration

from tests.common import MockConfigEntry


async def test_load_integration(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_light: Mock,
    mock_room: Mock,
) -> None:
    """Test load integration sets via device id for a light device to the hub device."""
    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [mock_light]

    with patch("homeassistant.components.fibaro.PLATFORMS", [Platform.LIGHT]):
        # Act
        await init_integration(hass, mock_config_entry)
        # Assert
        hub_device = device_registry.async_get_device({(DOMAIN, TEST_SERIALNUMBER)})
        light_device = device_registry.async_get_device(
            {(DOMAIN, mock_light.fibaro_id)}
        )
        assert hub_device.id == light_device.via_device_id


async def test_via_device_id(
    hass: HomeAssistant,
    mock_fibaro_client: Mock,
    mock_config_entry: MockConfigEntry,
    mock_light: Mock,
    mock_room: Mock,
) -> None:
    """Test unload integration stops state listener."""
    # Arrange
    mock_fibaro_client.read_rooms.return_value = [mock_room]
    mock_fibaro_client.read_devices.return_value = [mock_light]

    with patch("homeassistant.components.fibaro.PLATFORMS", [Platform.LIGHT]):
        await init_integration(hass, mock_config_entry)
        # Act
        await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        # Assert
        assert mock_fibaro_client.unregister_update_handler.call_count == 1
