install:
	pip install "homeassistant==`cat .HA_VERSION`"

test:
	hass -c . --script check_config --info all
