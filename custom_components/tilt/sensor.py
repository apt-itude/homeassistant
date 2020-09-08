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
    def uuid(self):
        return self.value

    @property
    def friendly_name(self):
        return self.name.capitalize()


PLATFORM_SCHEMA = homeassistant.components.sensor.PLATFORM_SCHEMA.extend(
    {vol.Required("color"): vol.Any(*[color.name.lower() for color in Color])}
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    color = Color.from_name(config["color"])
    tilt = Tilt(color)

    mqtt_subscriber = MQTTSubscriber(tilt, hass)

    hass.bus.listen_once(
        homeassistant.const.EVENT_HOMEASSISTANT_START,
        lambda _event: mqtt_subscriber.start(),
    )
    hass.bus.listen_once(
        homeassistant.const.EVENT_HOMEASSISTANT_STOP,
        lambda _event: mqtt_subscriber.stop(),
    )
    mqtt_subscriber.start()

    _LOG.debug("Adding sensor entities for Tilt %s", color.friendly_name)
    add_entities([TemperatureSensor(tilt), SpecificGravitySensor(tilt)])


class Tilt:
    def __init__(self, color):
        self._color = color
        self.temperature = None
        self.specific_gravity = None

    @property
    def color(self):
        return self._color


class MQTTSubscriber:
    def __init__(self, tilt, hass):
        self._tilt = tilt
        self._hass = hass
        self._unsubscribe = None

    @property
    def _topic(self):
        return f"ibeacon/{self._tilt.color.uuid}"

    def start(self):
        if self._unsubscribe is not None:
            _LOG.debug("Already subscribed to topic %s", self._topic)
            return

        self._unsubscribe = homeassistant.components.mqtt.subscribe(
            self._hass, self._topic, self._handle_message
        )
        _LOG.debug("Subscribed to topic %s", self._topic)

    @homeassistant.core.callback
    def _handle_message(self, message):
        _LOG.debug(
            "Received Tilt %s iBeacon advertisement via MQTT",
            self._tilt.color.friendly_name,
        )

        try:
            data = json.loads(message.payload)
        except json.JSONDecodeError:
            _LOG.error("Failed to decode iBeacon payload as JSON: %s", message.payload)

        try:
            self._tilt.temperature = data["major"]
        except KeyError:
            _LOG.error("iBeacon payload is missing 'major' field")

        try:
            self._tilt.specific_gravity = float(data["minor"]) / 1000
        except KeyError:
            _LOG.error("iBeacon payload is missing 'minor' field")

    def stop(self):
        if self._unsubscribe is None:
            _LOG.debug("Not subscribed to topic %s", self._topic)
            return

        self._unsubscribe()
        self._unsubscribe = None
        _LOG.debug("Unsubscribed from topic %s", self._topic)


class TemperatureSensor(homeassistant.helpers.entity.Entity):
    def __init__(self, tilt):
        self._tilt = tilt

    @property
    def name(self):
        return f"Tilt {self._tilt.color.friendly_name} Temperature"

    @property
    def state(self):
        return self._tilt.temperature

    @property
    def unit_of_measurement(self):
        return homeassistant.const.TEMP_FAHRENHEIT

    @property
    def available(self):
        return self._tilt.temperature is not None


class SpecificGravitySensor(homeassistant.helpers.entity.Entity):
    def __init__(self, tilt):
        self._tilt = tilt

    @property
    def name(self):
        return f"Tilt {self._tilt.color.friendly_name} Specific Gravity"

    @property
    def state(self):
        return self._tilt.specific_gravity

    @property
    def available(self):
        return self._tilt.specific_gravity is not None
