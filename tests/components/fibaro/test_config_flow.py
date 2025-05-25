"""Test the Fibaro config flow."""

from ipaddress import IPv4Address
from unittest.mock import Mock

from pyfibaro.fibaro_client import FibaroAuthenticationFailed, FibaroConnectFailed
import pytest
from requests.exceptions import HTTPError

from homeassistant import config_entries
from homeassistant.components.fibaro import DOMAIN
from homeassistant.components.fibaro.config_flow import _normalize_url
from homeassistant.components.fibaro.const import CONF_IMPORT_PLUGINS
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .conftest import (
    TEST_NAME,
    TEST_PASSWORD,
    TEST_SERIALNUMBER,
    TEST_URL,
    TEST_USERNAME,
)

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry", "mock_fibaro_client")

MOCK_ZEROCONF_DISCOVERY_INFO = ZeroconfServiceInfo(
    ip_address=IPv4Address(address="192.168.1.1"),
    ip_addresses=[IPv4Address(address="192.168.1.1")],
    hostname=f"${TEST_SERIALNUMBER}.local",
    name=f"${TEST_SERIALNUMBER}",
    port=22,
    properties={},
    type="_ssh._tcp.local.",
)

MOCK_ZEROCONF_DISCOVERY_INFO_IP_CHANGE = ZeroconfServiceInfo(
    ip_address=IPv4Address(address="192.168.1.2"),
    ip_addresses=[IPv4Address(address="192.168.1.2")],
    hostname=f"${TEST_SERIALNUMBER}.local",
    name=f"${TEST_SERIALNUMBER}",
    port=22,
    properties={},
    type="_ssh._tcp.local.",
)


async def _recovery_after_failure_works(
    hass: HomeAssistant, mock_fibaro_client: Mock, result: FlowResult
) -> None:
    mock_fibaro_client.connect_with_credentials.side_effect = None
    mock_fibaro_client.connect_with_credentials.return_value = (
        mock_fibaro_client.read_info()
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_URL: TEST_URL,
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
        CONF_IMPORT_PLUGINS: False,
    }


async def _recovery_after_reauth_failure_works(
    hass: HomeAssistant, mock_fibaro_client: Mock, result: FlowResult
) -> None:
    mock_fibaro_client.connect_with_credentials.side_effect = None
    mock_fibaro_client.connect_with_credentials.return_value = (
        mock_fibaro_client.read_info()
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "other_fake_password"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_config_flow_user_initiated_success(hass: HomeAssistant) -> None:
    """Successful flow manually initialized by the user."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_URL: TEST_URL,
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
        CONF_IMPORT_PLUGINS: False,
    }


async def test_config_flow_user_initiated_auth_failure(
    hass: HomeAssistant, mock_fibaro_client: Mock
) -> None:
    """Authentication failure in flow manually initialized by the user."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    mock_fibaro_client.connect_with_credentials.side_effect = (
        FibaroAuthenticationFailed()
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}

    await _recovery_after_failure_works(hass, mock_fibaro_client, result)


async def test_config_flow_user_initiated_connect_failure(
    hass: HomeAssistant, mock_fibaro_client: Mock
) -> None:
    """Unknown failure in flow manually initialized by the user."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    mock_fibaro_client.connect_with_credentials.side_effect = FibaroConnectFailed()

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}

    await _recovery_after_failure_works(hass, mock_fibaro_client, result)


async def test_reauth_success(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Successful reauth flow initialized by the user."""
    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "other_fake_password"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_reauth_connect_failure(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_fibaro_client: Mock,
) -> None:
    """Successful reauth flow initialized by the user."""
    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}

    mock_fibaro_client.connect_with_credentials.side_effect = FibaroConnectFailed()

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "other_fake_password"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "cannot_connect"}

    await _recovery_after_reauth_failure_works(hass, mock_fibaro_client, result)


async def test_reauth_auth_failure(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_fibaro_client: Mock,
) -> None:
    """Successful reauth flow initialized by the user."""
    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}

    mock_fibaro_client.connect_with_credentials.side_effect = (
        FibaroAuthenticationFailed()
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "other_fake_password"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "invalid_auth"}

    await _recovery_after_reauth_failure_works(hass, mock_fibaro_client, result)


@pytest.mark.parametrize("url_path", ["/api/", "/api", "/", ""])
async def test_normalize_url(url_path: str) -> None:
    """Test that the url is normalized for different entered values."""
    assert _normalize_url(f"http://192.168.1.1{url_path}") == "http://192.168.1.1/api/"


async def test_zeroconf_with_unknown_device(
    hass: HomeAssistant, mock_fibaro_client_config_flow: Mock
) -> None:
    """Test the zeroconf setup case."""
    mock_fibaro_client_config_flow.read_info.side_effect = HTTPError()

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=MOCK_ZEROCONF_DISCOVERY_INFO,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_fibaro_hub"


async def test_zeroconf_discovery(
    hass: HomeAssistant, mock_fibaro_client_config_flow: Mock
) -> None:
    """Test discovery of fibaro hub."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=MOCK_ZEROCONF_DISCOVERY_INFO,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}
