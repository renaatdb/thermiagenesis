import logging

from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import Entity
from pythermiagenesis.const import ATTR_INPUT_COMPRESSOR_SPEED_RPM
from pythermiagenesis.const import ATTR_INPUT_HOT_WATER_DIRECTIONAL_VALVE_POSITION
from pythermiagenesis.const import ATTR_INPUT_MIX_VALVE_COOLING_OPENING_DEGREE
from pythermiagenesis.const import REGISTERS

from .const import ATTR_CLASS
from .const import ATTR_DEFAULT_ENABLED
from .const import ATTR_ICON
from .const import ATTR_LABEL
from .const import ATTR_MANUFACTURER
from .const import ATTR_STATE_CLASS
from .const import ATTR_UNIT
from .const import DOMAIN
from .const import HEATPUMP_ALARMS
from .const import HEATPUMP_ATTRIBUTES
from .const import HEATPUMP_SENSOR
from .const import SENSOR_TYPES

ATTR_COUNTER = "counter"
ATTR_FIRMWARE = "firmware"

# BELANGRIJK:
# Deze oude identifier behouden we bewust.
# Daardoor blijft Home Assistant hetzelfde bestaande apparaat gebruiken.
ATTR_DEVICE_IDENTIFIER = "Diplomat Inverter Duo"

# Dit is de correcte zichtbare apparaatnaam en het correcte model.
ATTR_MODEL = "Calibra Cool 7 BW"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add Thermia entities from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    sensors = []

    device_info = {
        # Bestaande identifier behouden om geen tweede HA-apparaat te creëren.
        "identifiers": {(DOMAIN, ATTR_DEVICE_IDENTIFIER)},

        # Correcte zichtbare naam en correct model.
        "name": ATTR_MODEL,
        "manufacturer": ATTR_MANUFACTURER,
        "model": ATTR_MODEL,
        "sw_version": coordinator.data.get(ATTR_FIRMWARE),
    }

    sensors.append(
        ThermiaHeatpumpSensor(
            coordinator,
            HEATPUMP_SENSOR,
            device_info,
        )
    )

    for sensor in SENSOR_TYPES:
        if REGISTERS[sensor][coordinator.kind]:
            sensors.append(
                ThermiaGenericSensor(
                    coordinator,
                    sensor,
                    device_info,
                )
            )

    # Calibra/Calibra Cool exposes input register 47 as the tap-water
    # directional valve position. pythermiagenesis knows this register but
    # marks it unsupported for the generic "inverter" model, so the upstream
    # integration filters it out. Read it explicitly in this Calibra fork.
    sensors.append(
        ThermiaTapWaterValvePositionSensor(
            coordinator,
            ATTR_INPUT_HOT_WATER_DIRECTIONAL_VALVE_POSITION,
            device_info,
        )
    )

    async_add_entities(sensors, False)


class ThermiaHeatpumpSensor(Entity):
    """Define a Thermia heatpump sensor."""

    def __init__(self, coordinator, kind, device_info):
        """Initialize."""
        self._name = "Heatpump"
        self._unique_id = "thermiagenesis_heatpump"
        self._device_info = device_info
        self.coordinator = coordinator
        self.kind = kind
        self._attrs = {}

    @property
    def name(self):
        """Return the name."""
        return self._name

    def is_passive_cooling(self):
        """Return True when the Calibra is producing passive cooling."""
        valve_opening = self.coordinator.data.get(
            ATTR_INPUT_MIX_VALVE_COOLING_OPENING_DEGREE
        )

        compressor_rpm = self.coordinator.data.get(
            ATTR_INPUT_COMPRESSOR_SPEED_RPM
        )

        # Beide echte Modbuswaarden moeten beschikbaar zijn.
        #
        # Een ontbrekende waarde mag niet als 0 worden geïnterpreteerd,
        # omdat we anders ten onrechte "Passive Cooling" zouden kunnen
        # rapporteren.
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
    def state(self):
        """Return the state."""
        val = self.coordinator.data.get(self.kind)

        # De standaard Genesis-status blijft bij de Calibra soms "OFF"
        # terwijl er werkelijk passieve koeling actief is.
        #
        # Daarom corrigeren we alleen de OFF-toestand wanneer:
        # - de koelklep werkelijk geopend is;
        # - de compressor werkelijk 0 rpm draait.
        if str(val).lower() == "off" and self.is_passive_cooling():
            return "Passive Cooling"

        return val

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        for attr in HEATPUMP_ATTRIBUTES:
            label = (attr[0].split("_", 1)[-1]).title()
            val = self.coordinator.data.get(attr[0])

            if attr[1]:
                val = f"{val} {attr[1]}"

            self._attrs[label] = val

        if self.has_alarm():
            self._attrs["Active alarms"] = ""

        return self._attrs

    @property
    def icon(self):
        """Return the icon."""
        if self.has_alarm():
            return "mdi-alert"

        if self.is_passive_cooling():
            return "mdi-snowflake"

        return "mdi-pulse"

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return self._unique_id

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return SENSOR_TYPES[self.kind].get(ATTR_UNIT, None)

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
        """Return if the entity should be enabled by default."""
        return True

    def has_alarm(self):
        """Return True when one or more heat-pump alarms are active."""
        for alarm in HEATPUMP_ALARMS:
            if self.coordinator.data.get(alarm):
                return True

        return False

    def async_write_ha_state(self):
        """Write the latest state to Home Assistant."""
        super().async_write_ha_state()

    async def async_added_to_hass(self):
        """Register all attributes required by the heat-pump entity."""
        register_attr = [
            self.kind,

            # Nodig voor betrouwbare detectie van passieve koeling.
            ATTR_INPUT_MIX_VALVE_COOLING_OPENING_DEGREE,
            ATTR_INPUT_COMPRESSOR_SPEED_RPM,
        ]

        for attr in HEATPUMP_ATTRIBUTES:
            register_attr.append(attr[0])

        self.coordinator.registerAttribute(register_attr)

        self.async_on_remove(
            self.coordinator.async_add_listener(
                self.async_write_ha_state
            )
        )

    async def async_update(self):
        """Update Thermia entity."""
        await self.coordinator.async_request_refresh()


class ThermiaGenericSensor(Entity):
    """Define a Thermia generic sensor."""

    def __init__(self, coordinator, kind, device_info):
        """Initialize."""
        self._name = f"{SENSOR_TYPES[kind][ATTR_LABEL]}"
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
    def state(self):
        """Return the state."""
        return self.coordinator.data.get(self.kind)

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attrs

    @property
    def icon(self):
        """Return the icon."""
        return SENSOR_TYPES[self.kind][ATTR_ICON]

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return self._unique_id

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return SENSOR_TYPES[self.kind].get(ATTR_UNIT, None)

    @property
    def device_class(self):
        """Return the device class."""
        return SENSOR_TYPES[self.kind].get(ATTR_CLASS, None)

    @property
    def state_class(self):
        """Return the state class."""
        return SENSOR_TYPES[self.kind].get(
            ATTR_STATE_CLASS,
            SensorStateClass.MEASUREMENT,
        )

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

    def async_write_ha_state(self):
        """Write the latest state to Home Assistant."""
        super().async_write_ha_state()

    @property
    def entity_registry_enabled_default(self):
        """Return whether the entity is enabled by default."""
        return SENSOR_TYPES[self.kind][ATTR_DEFAULT_ENABLED]

    async def async_added_to_hass(self):
        """Register the Modbus attribute used by this sensor."""
        await super().async_added_to_hass()

        self.coordinator.registerAttribute(self.kind)

        self.async_on_remove(
            self.coordinator.async_add_listener(
                self.async_write_ha_state
            )
        )

    async def async_update(self):
        """Update Thermia entity."""
        await self.coordinator.async_request_refresh()


class ThermiaTapWaterValvePositionSensor(ThermiaGenericSensor):
    """Expose the Calibra tap-water directional valve position."""

    def __init__(self, coordinator, kind, device_info):
        """Initialize."""
        super().__init__(
            coordinator,
            kind,
            device_info,
        )

        self._name = "Tap Water Valve Position"

    @property
    def unit_of_measurement(self):
        """Return the valve position as a percentage."""
        return PERCENTAGE

    @property
    def entity_registry_enabled_default(self):
        """Enable this Calibra-specific sensor by default."""
        return True
