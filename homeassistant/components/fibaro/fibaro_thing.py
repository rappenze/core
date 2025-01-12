"""Fibaro manager."""

from pyfibaro.fibaro_device import DeviceModel


class FibaroThing:
    """Higher level access to fibaro API."""

    def __init__(self, master: DeviceModel, endpoints: list[DeviceModel]) -> None:
        """Create a new thing by serving the master and the child endpoints."""
        self._master = master
        self._endpoints = endpoints

    def get_master(self) -> DeviceModel:
        """Get master endpoint."""
        return self._master

    def get_endpoints(self) -> list[DeviceModel]:
        """Get child endpoints or empty list."""
        return self._endpoints
