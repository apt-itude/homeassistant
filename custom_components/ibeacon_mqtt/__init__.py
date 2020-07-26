import logging

import beacontools
import homeassistant.components
import homeassistant.const


DOMAIN = "ibeacon_mqtt"

_LOG = logging.getLogger(__name__)


def setup(hass, config):
    monitor = iBeaconMonitor()

    hass.bus.listen_once(homeassistant.const.EVENT_HOMEASSISTANT_START, monitor.start)
    hass.bus.listen_once(homeassistant.const.EVENT_HOMEASSISTANT_STOP, monitor.stop)

    monitor.start()

    return True


class iBeaconMonitor:
    def __init__(self):
        self._scanner = None

    def start(self):
        if self._scanner is not None:
            _LOG.debug("Already scanning for iBeacons")
            return

        self._scanner = beacontools.BeaconScanner(
            self._handle_beacon, packet_filter=beacontools.IBeaconAdvertisement
        )
        self._scanner.start()
        _LOG.info("Started scanning for iBeacons")

    def _handle_beacon(self, bt_addr, rssi, packet, additional_info):
        _LOG.debug(
            "Received iBeacon: <%s, %d> %s %s", bt_addr, rssi, packet, additional_info
        )
        try:
            topic = f"ibeacon/{packet.uuid}"
            payload = {
                "major": packet.major,
                "minor": packet.minor,
            }
            homeassistant.components.mqtt.publish(hass, topic, payload)
        except Exception:
            _LOG.exception("Failed to publish iBeacon data to MQTT")

    def stop(self):
        if self._scanner is None:
            _LOG.debug("Already not scanning for iBeacons")
            return

        self._scanner.stop()
        self._scanner = None
        _LOG.info("Stopped scanning for iBeacons")
