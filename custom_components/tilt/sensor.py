import enum
import logging

import beacontools
import homeassistant.const
import homeassistant.helpers.entity


_LOG = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    tilts = {color: Tilt(color) for color in [Color.BLACK]}

    monitor = iBeaconMonitor(tilts)

    hass.bus.listen_once(homeassistant.const.EVENT_HOMEASSISTANT_START, monitor.start)
    hass.bus.listen_once(homeassistant.const.EVENT_HOMEASSISTANT_STOP, monitor.stop)

    monitor.start()

    add_entities([TemperatureSensor(tilt) for tilt in tilts.values()])


class Color(enum.Enum):
    RED = "a495bb10-c5b1-4b44-b512-1370f02d74de"
    GREEN = "a495bb20-c5b1-4b44-b512-1370f02d74de"
    BLACK = "a495bb30-c5b1-4b44-b512-1370f02d74de"
    PURPLE = "a495bb40-c5b1-4b44-b512-1370f02d74de"
    ORANGE = "a495bb50-c5b1-4b44-b512-1370f02d74de"
    BLUE = "a495bb60-c5b1-4b44-b512-1370f02d74de"
    YELLOW = "a495bb70-c5b1-4b44-b512-1370f02d74de"
    PINK = "a495bb80-c5b1-4b44-b512-1370f02d74de"

    @property
    def uuid(self):
        return self.value

    @property
    def friendly_name(self):
        return self.name.capitalize()


class Tilt:
    def __init__(self, color):
        self._color = color
        self.temperature = None
        self.specific_gravity = None

    @property
    def color(self):
        return self.color


class iBeaconMonitor:
    def __init__(self, tilts):
        self._tilts = tilts
        self._scanner = None

    def start(self):
        if self._scanner is not None:
            _LOG.debug("Already scanning for iBeacons")
            return

        self._scanner = beacontools.BeaconScanner(
            self._handle_beacon,
            device_filter=[
                beacontools.IBeaconFilter(uuid=color.uuid)
                for color in self._tilts.keys()
            ],
        )
        self._scanner.start()
        _LOG.info("Started scanning for iBeacons")

    def _handle_beacon(self, bt_addr, rssi, packet, additional_info):
        _LOG.debug(
            "Received iBeacon: <%s, %d> %s %s", bt_addr, rssi, packet, additional_info
        )
        color = Color(packet.uuid.lower())
        try:
            tilt = self._tilts[color]
        except KeyError:
            _LOG.error("Not monitoring for Tilt %s", color.friendly_name)
            return

        _LOG.debug("Updating Tilt %s", color.friendly_name)
        tilt.update(packet.major, packet.minor)

    def stop(self):
        if self._scanner is None:
            _LOG.debug("Already not scanning for iBeacons")
            return

        self._scanner.stop()
        self._scanner = None
        _LOG.info("Stopped scanning for iBeacons")


class TemperatureSensor(homeassistant.helpers.entity.Entity):
    def __init__(self, tilt):
        self._tilt = tilt

    @property
    def name(self):
        return f"Tilt {self.tilt.color.friendly_name} Temperature"

    @property
    def state(self):
        return self.tilt.temperature

    @property
    def unit_of_measurement(self):
        return homeassistant.const.TEMP_FAHRENHEIT

    @property
    def available(self):
        return self.tilt.temperature is not None
