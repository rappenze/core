"""Fibaro data class is a data reader for the different fibaro API endpoints."""

from pyfibaro.fibaro_client import FibaroClient, InfoModel
from pyfibaro.fibaro_device import DeviceModel
from pyfibaro.fibaro_scene import SceneModel

from .fibaro_thing import FibaroThing


class FibaroData:
    """Higher level access to fibaro API data."""

    def __init__(
        self, fibaro_client: FibaroClient, load_devices_from_plugins: bool = False
    ) -> None:
        """Read all fibaro data from the API."""
        self._fibaro_info = fibaro_client.read_info()
        self._fibaro_scenes = fibaro_client.read_scenes()
        self._room_map = self._read_rooms(fibaro_client)
        self._fibaro_devices = fibaro_client.read_devices(
            fibaro_client, load_devices_from_plugins
        )

    def _read_rooms(self, fibaro_client: FibaroClient) -> dict[int, str]:
        return {room.fibaro_id: room.name for room in fibaro_client.read_rooms()}

    def _read_devices(
        self, fibaro_client: FibaroClient, load_devices_from_plugins: bool = False
    ) -> list[DeviceModel]:
        return [
            device
            for device in fibaro_client.read_devices()
            if device.enabled and (not device.is_plugin or load_devices_from_plugins)
        ]

    def get_room_name(self, room_id: int) -> str | None:
        """Get the room name by room id."""
        assert self._room_map
        return self._room_map.get(room_id, None)

    def get_scenes(self) -> list[SceneModel]:
        """Get all scenes."""
        return self._fibaro_scenes

    def get_hub_information(self) -> InfoModel:
        """Get information about the hub."""
        return self._fibaro_info

    def get_fibaro_things(self) -> list[FibaroThing]:
        """Get list of fibaro things. Each thing represents one physical device.

        A physical device can have several functions.
        """
        controller_ids = self._get_controller_ids()

        master_devices = [
            device
            for device in self._fibaro_devices
            if self._is_master_device(device, controller_ids)
        ]

        return [
            FibaroThing(
                master,
                [
                    endpoint
                    for endpoint in self._fibaro_devices
                    if endpoint.parent_fibaro_id == master.fibaro_id
                ],
            )
            for master in master_devices
        ]

    def _is_master_device(self, device: DeviceModel, controller_ids: set[int]) -> bool:
        return device.parent_fibaro_id in controller_ids or (
            device.parent_fibaro_id == 0 and device.fibaro_id not in controller_ids
        )

    def _get_controller_ids(self) -> set[int]:
        controller_types = {
            "com.fibaro.zwavePrimaryController",
            "com.fibaro.niceEngine",
            "com.fibaro.zigbeePrimaryController",
        }

        return {
            device.fibaro_id
            for device in self._fibaro_devices
            if device.type in controller_types
        }
