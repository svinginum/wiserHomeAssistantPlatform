"""Binary sensors.py"""

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA, DOMAIN, MANUFACTURER
from .helpers import get_device_name, get_identifier, get_room_name, get_unique_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up Wiser climate device."""
    data = hass.data[DOMAIN][config_entry.entry_id][DATA]  # Get Handler

    binary_sensors = []

    # Smoke alarm sensors
    for device in data.wiserhub.devices.smokealarms.all:
        binary_sensors.extend(
            [
                WiserSmokeAlarm(data, device.id, "Smoke Alarm"),
                WiserHeatAlarm(data, device.id, "Heat Alarm"),
                WiserTamperAlarm(data, device.id, "Tamper Alarm"),
                WiserFaultWarning(data, device.id, "Fault Warning"),
                WiserRemoteAlarm(data, device.id, "Remote Alarm"),
                WiserBatteryDefect(data, device.id, "Battery Defect"),
            ]
        )

    # Equipments sensors
    for device in data.wiserhub.devices.all:
        if hasattr(device, "equipment") and device.equipment:
            binary_sensors.extend(
                [
                    WiserEquipment(data, device.id, "Controllable", "equipment"),
                    WiserEquipment(data, device.id, "PCM Mode", "equipment"),
                ]
            )

    # Light sensors
    def flatten_devices(items):
        """Recursively flatten nested lists."""
        flat_list = []
        for item in items:
            if isinstance(item, list):
                flat_list.extend(flatten_devices(item))
            else:
                flat_list.append(item)
        return flat_list

    all_lights = flatten_devices(data.wiserhub.devices.lights.all)

    for device in all_lights:
        try:
            binary_sensors.extend(
                [
                    WiserStateIsDimmable(data, device.id, "Is Dimmable"),
                ]
            )
        except Exception as e:
            _LOGGER.error(f"Error setting up binary sensor for light {device.id if hasattr(device, 'id') else 'unknown'}: {e}")

    # Shutter binary sensors
    for device in data.wiserhub.devices.shutters.all:
        binary_sensors.extend(
            [
                WiserStateIsTiltSupported(data, device.id, "Is Tilt Supported"),
                WiserStateIsOpen(data, device.id, "Is Open"),
                WiserStateIsClosed(data, device.id, "Is Closed"),
            ]
        )

    # Binary sensors active
    for device in data.wiserhub.devices.binary_sensor.all:
        binary_sensors.extend([BaseBinarySensor(data, device.id, "Active")])

    async_add_entities(binary_sensors, True)


class BaseBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Base binary sensor class."""

    def __init__(
        self, coordinator, device_id=0, sensor_type="", device_data_key: str = ""
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._data = coordinator
        device = self._data.wiserhub.devices.get_by_id(device_id)
        # Handle multi-contact devices returning lists
        if isinstance(device, list):
            device = device[0] if len(device) > 0 else None
        self._device = device
        self._device_id = device_id
        self._device_name = None
        self._sensor_type = sensor_type
        self._device_data_key = device_data_key

        _LOGGER.info(
            f"{self._data.wiserhub.system.name} {self.name} initalise"
        )

        if self._device is None:
            _LOGGER.error(f"No device found for ID {device_id}")
            return

        if device_data_key and hasattr(self._device, device_data_key):
            self._state = getattr(
                getattr(self._device, device_data_key),
                self._sensor_type.replace(" ", "_").lower(),
            )
        else:
            self._state = getattr(
                self._device, self._sensor_type.replace(" ", "_").lower()
            )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug(f"{self.name} device update requested")
        device = self._data.wiserhub.devices.get_by_id(self._device_id)
        # Handle multi-contact devices
        if isinstance(device, list):
            device = device[0] if len(device) > 0 else None
        self._device = device
        
        if self._device is None:
            return
            
        if self._device_data_key and hasattr(self._device, self._device_data_key):
            self._state = getattr(
                getattr(self._device, self._device_data_key),
                self._sensor_type.replace(" ", "_").lower(),
            )
        else:
            self._state = getattr(
                self._device, self._sensor_type.replace(" ", "_").lower()
            )

        self.async_write_ha_state()

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{get_device_name(self._data, self._device_id)} {self._sensor_type}"

    @property
    def unique_id(self):
        """Return uniqueid."""
        return get_unique_id(self._data, "binary_sensor", self._sensor_type, self._device_id)

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "name": get_device_name(self._data, self._device_id),
            "identifiers": {(DOMAIN, get_identifier(self._data, self._device_id))},
            "manufacturer": MANUFACTURER,
            "model": self._device.product_type,
            "sw_version": self._device.firmware_version,
            "via_device": (DOMAIN, self._data.wiserhub.system.name),
        }


class WiserSmokeAlarm(BaseBinarySensor):
    """Smoke Alarm sensor."""

    _attr_device_class = BinarySensorDeviceClass.SMOKE

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the battery."""
        attrs = {}
        attrs["led_brightness"] = self._device.led_brightness
        attrs["alarm_sound_mode"] = self._device.alarm_sound_mode
        attrs["alarm_sound_level"] = self._device.alarm_sound_level
        attrs["life_time"] = self._device.life_time
        attrs["hush_duration"] = self._device.hush_duration
        return attrs


class WiserHeatAlarm(BaseBinarySensor):
    """Smoke Alarm sensor."""

    _attr_device_class = BinarySensorDeviceClass.HEAT


class WiserTamperAlarm(BaseBinarySensor):
    """Smoke Alarm sensor."""

    _attr_device_class = BinarySensorDeviceClass.TAMPER


class WiserFaultWarning(BaseBinarySensor):
    """Smoke Alarm sensor."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM


class WiserBatteryDefect(BaseBinarySensor):
    """Smoke Alarm battery defect sensor."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:battery-alert"


class WiserRemoteAlarm(BaseBinarySensor):
    """Smoke Alarm sensor."""


class WiserEquipment(BaseBinarySensor):
    """Base binary sensor class."""


class WiserStateIsDimmable(BaseBinarySensor):
    """Light IsDimmable sensor."""

    _attr_icon = "mdi:lightbulb-on-40"


class WiserStateIsTiltSupported(BaseBinarySensor):
    """Shutter Istilt supported  sensor."""


class WiserStateIsOpen(BaseBinarySensor):
    """Light IsDIs Open sensor."""

    _attr_device_class = BinarySensorDeviceClass.OPENING


class WiserStateIsClosed(BaseBinarySensor):
    """Light IsDimmable sensor."""

    _attr_device_class = BinarySensorDeviceClass.OPENING
    _attr_icon = "mdi:window-shutter"
