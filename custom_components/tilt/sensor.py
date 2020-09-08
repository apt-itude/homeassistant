import enum
import json
import logging

import homeassistant.components.mqtt
import homeassistant.components.sensor
import homeassistant.const
import homeassistant.core
import homeassistant.helpers.entity
import voluptuous as vol


_LOG = logging.getLogger(__name__)


class Color(enum.Enum):
    RED = "a495bb10-c5b1-4b44-b512-1370f02d74de"
    GREEN = "a495bb20-c5b1-4b44-b512-1370f02d74de"
    BLACK = "a495bb30-c5b1-4b44-b512-1370f02d74de"
    PURPLE = "a495bb40-c5b1-4b44-b512-1370f02d74de"
    ORANGE = "a495bb50-c5b1-4b44-b512-1370f02d74de"
    BLUE = "a495bb60-c5b1-4b44-b512-1370f02d74de"
    YELLOW = "a495bb70-c5b1-4b44-b512-1370f02d74de"
    PINK = "a495bb80-c5b1-4b44-b512-1370f02d74de"

    @classmethod
    def from_name(self, name):
        return getattr(self, name.upper())

    @property
    def friendly_name(self):
        return self.name.capitalize()


PLATFORM_SCHEMA = homeassistant.components.sensor.PLATFORM_SCHEMA.extend(
    {vol.Required("color"): vol.Any(*[color.name.lower() for color in Color])}
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    color = Color.from_name(config["color"])
    _LOG.debug("Adding sensor entities for Tilt %s", color.friendly_name)
    add_entities([TemperatureSensor(hass, color)])


class TemperatureSensor(homeassistant.helpers.entity.Entity):
    def __init__(self, hass, color):
        self._hass = hass
        self._color = color
        self._temperature = None
        self._unsubscribe = None

    @property
    def name(self):
        return f"Tilt {self._color.friendly_name} Temperature"

    @property
    def state(self):
        return self._temperature

    @property
    def unit_of_measurement(self):
        return homeassistant.const.TEMP_FAHRENHEIT

    @property
    def available(self):
        return self._temperature is not None

    @property
    def _topic(self):
        uuid = self._color.value
        return f"ibeacon/{uuid}"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._unsubscribe = await homeassistant.components.mqtt.async_subscribe(
            self._hass, self._topic, self._handle_message
        )

    @homeassistant.core.callback
    def _handle_message(self, message):
        _LOG.debug("Received Tilt iBeacon advertisement via MQTT")

        try:
            data = json.loads(message.payload)
        except json.JSONDecodeError:
            _LOG.error("Failed to decode iBeacon payload as JSON: %s", message.payload)

        try:
            self._temperature = data["major"]
        except KeyError:
            _LOG.error("iBeacon payload is missing 'major' field")

        self.schedule_update_ha_state()

    async def async_will_remove_from_hass(self):
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
