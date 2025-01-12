"""Fibaro manager."""

from collections.abc import Callable

from pyfibaro.fibaro_client import FibaroClient
from pyfibaro.fibaro_state_resolver import FibaroEvent, FibaroStateChange
from requests.exceptions import HTTPError


class FibaroManager:
    """Higher level access to fibaro API."""

    def __init__(self, url: str) -> None:
        """Construct the fibaro manager."""
        self._fibaro_client = FibaroClient(url)

        self._change_listeners: dict[
            int, list[Callable[[FibaroStateChange], None]]
        ] = {}
        self._event_listeners: dict[int, list[Callable[[FibaroEvent], None]]] = {}

    def connect(self, username: str, password: str) -> None:
        """Translate connect errors to easily differentiate auth and connect failures."""
        try:
            self._fibaro_client.set_authentication(username, password)
            self._fibaro_client.connect()
        except HTTPError as http_ex:
            if http_ex.response.status_code == 403:
                raise FibaroAuthenticationFailed from http_ex
            raise FibaroConnectFailed from http_ex
        except Exception as ex:
            raise FibaroConnectFailed from ex

    def add_change_listener(
        self, fibaro_id: int, listener: Callable[[FibaroStateChange], None]
    ) -> Callable[[], None]:
        """Add a listener to get property changes."""
        change_listeners = self._change_listeners.setdefault(fibaro_id, [])
        change_listeners.append(listener)

        return lambda: change_listeners.remove(listener)

    def add_event_listener(
        self, fibaro_id: int, listener: Callable[[FibaroEvent], None]
    ) -> Callable[[], None]:
        """Add central scene event listener."""
        event_listeners = self._event_listeners.setdefault(fibaro_id, [])
        event_listeners.append(listener)

        return lambda: event_listeners.remove(listener)


class FibaroConnectFailed(Exception):
    """Error to indicate we cannot connect to fibaro home center."""


class FibaroAuthenticationFailed(Exception):
    """Error to indicate that authentication failed on fibaro home center."""
