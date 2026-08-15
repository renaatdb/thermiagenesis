import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from pythermiagenesis.const import ATTR_INPUT_COMPRESSOR_SPEED_RPM
from pythermiagenesis.const import ATTR_INPUT_MIX_VALVE_COOLING_OPENING_DEGREE
from pythermiagenesis.const import REGISTERS

from .const import ATTR_CLASS
from .const import ATTR_DEFAULT_ENABLED
from .const import ATTR_LABEL
from .const import ATTR_MANUFACTURER
from .const import BINARY_SENSOR_TYPES
from .const import DOMAIN

ATTR_COUNTER = "counter"
ATTR_FIRMWARE = "firmware"

# Bestaande Home Assistant device-identifier bewust behouden.
# Hierdoor wordt geen tweede Thermia-apparaat aangemaakt.
ATTR_DEVICE_IDENTIFIER = "Diplomat Inverter Duo"

# Correcte zichtbare apparaatnaam en model.
ATTR_MODEL = "Calibra Cool 7 BW"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add Thermia entities from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    sensors = []

    device_info = {
        # Oude identifier behouden zodat HA hetzelfde apparaat blijft gebruiken.
        "identifiers": {(DOMAIN, ATTR_DEVICE_IDENTIFIER)},

        # Correcte zichtbare informatie.
        "name": ATTR_MODEL,
        "manufacturer": ATTR_MANUFACTURER,
        "model": ATTR_MODEL,
        "sw_version": coordinator.data.get(ATTR_FIRMWARE),
    }

    for sensor in BINARY_SENSOR_TYPES:
        if REGISTERS[sensor][coordinator.kind]:
            sensors.append(
                ThermiaBinarySensor(
                    coordinator,
                    sensor,
                    device_info,
                )
            )

    # Calibra/Calibra Cool does not reliably assert the built-in
    # "mixing valve 1 is producing passive cooling" discrete input.
    #
    # Derive a reliable read-only state from:
    # - the actual cooling-valve opening;
    # - the actual compressor speed.
    #
    # This behaviour has been verified on a Calibra Cool 7 BW.
    sensors.append(
        ThermiaPassiveCoolingSensor(
            coordinator,
            device_info,
        )
    )

    async_add_entities(sensors, False)


class ThermiaBinarySensor(BinarySensorEntity):
    """Define a Thermia generic binary sensor."""

    def __init__(self, coordinator, kind, device_info):
        """Initialize."""
        self._name = f"{BINARY_SENSOR_TYPES[kind][ATTR_LABEL]}"
        self._unique_id = f"thermiagenesis_{kind}"
        self._device_info = device_info
        self.coordinator = coordinator
        self.kind = kind
        self._attrs = {}

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def is_on(self):
        """Return the state."""
        return self.coordinator.data.get(self.kind)

    @property
    def device_class(self):
        """Return the device class."""
        if ATTR_CLASS not in BINARY_SENSOR_TYPES[self.kind]:
            return None

        return BINARY_SENSOR_TYPES[self.kind][ATTR_CLASS]

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attrs

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return self._unique_id

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def should_poll(self):
        """Return the polling requirement of the entity."""
        return False

    @property
    def device_info(self):
        """Return the device info."""
        return self._device_info

    @property
    def entity_registry_enabled_default(self):
        """Return whether the entity should be enabled by default."""
        return BINARY_SENSOR_TYPES[self.kind][ATTR_DEFAULT_ENABLED]

    def async_write_ha_state(self):
        """Write the latest state to Home Assistant."""
        super().async_write_ha_state()

    async def async_added_to_hass(self):
        """Register attribute and listen for coordinator updates."""
        self.coordinator.registerAttribute(self.kind)

        self.async_on_remove(
            self.coordinator.async_add_listener(
                self.async_write_ha_state
            )
        )

    async def async_update(self):
        """Update Thermia entity."""
        await self.coordinator.async_request_refresh()


class ThermiaPassiveCoolingSensor(BinarySensorEntity):
    """Expose a reliable Calibra passive-cooling state."""

    def __init__(self, coordinator, device_info):
        """Initialize the passive cooling binary sensor."""
        self._attr_name = "Passive Cooling Active"
        self._attr_unique_id = "thermiagenesis_passive_cooling_active"
        self._attr_icon = "mdi-snowflake"
        self._device_info = device_info
        self.coordinator = coordinator

    @property
    def is_on(self):
        """Return True while passive cooling is actually running."""
        valve_opening = self.coordinator.data.get(
            ATTR_INPUT_MIX_VALVE_COOLING_OPENING_DEGREE
        )

        compressor_rpm = self.coordinator.data.get(
            ATTR_INPUT_COMPRESSOR_SPEED_RPM
        )

        # Beide echte Modbuswaarden moeten beschikbaar zijn.
        #
        # Een ontbrekende waarde mag niet als 0 worden geïnterpreteerd.
        # Anders zou bijvoorbeeld een ontbrekende compressorwaarde
        # ten onrechte als 0 rpm kunnen worden beschouwd.
        if valve_opening is None or compressor_rpm is None:
            return False

        try:
            return (
                float(valve_opening) > 0
                and float(compressor_rpm) == 0
            )
        except (TypeError, ValueError):
            return False

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def should_poll(self):
        """Return the polling requirement of the entity."""
        return False

    @property
    def device_info(self):
        """Return the device info."""
        return self._device_info

    @property
    def entity_registry_enabled_default(self):
        """Enable the Calibra passive-cooling status by default."""
        return True

    def async_write_ha_state(self):
        """Write the latest state to Home Assistant."""
        super().async_write_ha_state()

    async def async_added_to_hass(self):
        """Register the required Modbus input registers."""
        self.coordinator.registerAttribute(
            [
                ATTR_INPUT_MIX_VALVE_COOLING_OPENING_DEGREE,
                ATTR_INPUT_COMPRESSOR_SPEED_RPM,
            ]
        )

        self.async_on_remove(
            self.coordinator.async_add_listener(
                self.async_write_ha_state
            )
        )

    async def async_update(self):
        """Update Thermia entity."""
        await self.coordinator.async_request_refresh()
