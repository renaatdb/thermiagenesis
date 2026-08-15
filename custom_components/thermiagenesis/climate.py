"""Thermia Genesis climate sensors."""

import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ATTR_CURRENT_TEMPERATURE
from homeassistant.components.climate.const import ATTR_MAX_TEMP
from homeassistant.components.climate.const import ATTR_MIN_TEMP
from homeassistant.components.climate.const import ATTR_TARGET_TEMP_HIGH
from homeassistant.components.climate.const import ATTR_TARGET_TEMP_LOW
from homeassistant.components.climate.const import ATTR_TARGET_TEMP_STEP
from homeassistant.components.climate.const import ClimateEntityFeature
from homeassistant.components.climate.const import HVACAction
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.const import UnitOfTemperature
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import ATTR_DEFAULT_ENABLED
from .const import ATTR_ENABLED
from .const import ATTR_LABEL
from .const import ATTR_MANUFACTURER
from .const import ATTR_STATUS
from .const import CLIMATE_TYPES
from .const import DOMAIN
from .const import KEY_STATUS_VALUE

ATTR_FIRMWARE = "firmware"

# Bestaande Home Assistant device-identifier bewust behouden.
# Zo blijft dit hetzelfde bestaande apparaat in de device registry.
ATTR_DEVICE_IDENTIFIER = "Diplomat Inverter Duo"

# Correcte zichtbare apparaatnaam en model.
ATTR_MODEL = "Calibra Cool 7 BW"

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = ClimateEntityFeature(0)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add Thermia entities from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    sensors = []

    device_info = {
        # Oude identifier behouden zodat Home Assistant
        # geen tweede Thermia-apparaat aanmaakt.
        "identifiers": {(DOMAIN, ATTR_DEVICE_IDENTIFIER)},

        # Correcte zichtbare apparaat-info.
        "name": ATTR_MODEL,
        "manufacturer": ATTR_MANUFACTURER,
        "model": ATTR_MODEL,
        "sw_version": coordinator.data.get(ATTR_FIRMWARE),
    }

    for sensor in CLIMATE_TYPES:
        sensors.append(
            ThermiaClimateSensor(
                coordinator,
                sensor,
                device_info,
            )
        )

    async_add_entities(sensors, False)


class ThermiaClimateSensor(ClimateEntity):
    """Define a Thermia climate sensor."""

    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, coordinator, kind, device_info):
        """Initialize."""
        self.kind = kind
        self.meta = CLIMATE_TYPES[kind]
        self._name = f"{self.meta[ATTR_LABEL]}"
        self._unique_id = f"thermiagenesis_{kind}"
        self._device_info = device_info
        self.coordinator = coordinator
        self._hvac_mode = HVACAction.IDLE
        self._attrs = {}

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement used by the platform."""
        return UnitOfTemperature.CELSIUS

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        ret = SUPPORT_FLAGS
        ret |= ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF

        if ATTR_TEMPERATURE in self.meta:
            ret |= ClimateEntityFeature.TARGET_TEMPERATURE

        if (
            ATTR_TARGET_TEMP_HIGH in self.meta
            and ATTR_TARGET_TEMP_LOW in self.meta
        ):
            ret |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE

        return ret

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def current_temperature(self):
        """Return the current temperature."""
        val = self.coordinator.data.get(
            self.meta[ATTR_CURRENT_TEMPERATURE]
        )
        return val

    @property
    def target_temperature_low(self):
        """Return the target low temperature."""
        if ATTR_TARGET_TEMP_LOW not in self.meta:
            return None

        val = self.coordinator.data.get(
            self.meta[ATTR_TARGET_TEMP_LOW]
        )
        return val

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return TemperatureConverter.convert(
            self.meta[ATTR_MIN_TEMP],
            UnitOfTemperature.CELSIUS,
            self.temperature_unit,
        )

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return TemperatureConverter.convert(
            self.meta[ATTR_MAX_TEMP],
            UnitOfTemperature.CELSIUS,
            self.temperature_unit,
        )

    @property
    def target_temperature_high(self):
        """Return the target high temperature."""
        if ATTR_TARGET_TEMP_HIGH not in self.meta:
            return None

        val = self.coordinator.data.get(
            self.meta[ATTR_TARGET_TEMP_HIGH]
        )
        return val

    @property
    def target_temperature_step(self):
        """Return the target temperature step."""
        if ATTR_TARGET_TEMP_STEP not in self.meta:
            return 1

        val = self.meta[ATTR_TARGET_TEMP_STEP]
        return val

    @property
    def target_temperature(self):
        """Return the target temperature."""
        if ATTR_TEMPERATURE not in self.meta:
            return None

        val = self.coordinator.data.get(
            self.meta[ATTR_TEMPERATURE]
        )
        return val

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
        """Return if the entity should be enabled when first added."""
        return self.meta[ATTR_DEFAULT_ENABLED]

    @property
    def hvac_action(self):
        """Return the current running HVAC operation."""
        is_enabled = self.coordinator.data.get(
            self.meta[ATTR_ENABLED]
        )

        if not is_enabled:
            return HVACAction.OFF

        val = self.coordinator.data.get(ATTR_STATUS)

        if val == self.meta[KEY_STATUS_VALUE]:
            return HVACAction.HEATING

        return HVACAction.IDLE

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        is_enabled = self.coordinator.data.get(
            self.meta[ATTR_ENABLED]
        )

        if not is_enabled:
            return HVACMode.OFF

        val = self.coordinator.data.get(ATTR_STATUS)

        if val == self.meta[KEY_STATUS_VALUE]:
            return HVACMode.HEAT

        return HVACMode.AUTO

    @property
    def hvac_modes(self):
        """Return supported HVAC modes."""
        return [
            HVACMode.OFF,
            HVACMode.AUTO,
        ]

    async def async_set_hvac_mode(self, hvac_mode: str):
        """Set new target HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator._async_set_data(
                self.meta[ATTR_ENABLED],
                False,
            )

        if hvac_mode == HVACMode.AUTO:
            await self.coordinator._async_set_data(
                self.meta[ATTR_ENABLED],
                True,
            )

    async def async_turn_on(self):
        """Turn the climate entity on."""
        await self.coordinator._async_set_data(
            self.meta[ATTR_ENABLED],
            True,
        )

    async def async_turn_off(self):
        """Turn the climate entity off."""
        await self.coordinator._async_set_data(
            self.meta[ATTR_ENABLED],
            False,
        )

    def async_write_ha_state(self):
        """Write the latest state to Home Assistant."""
        super().async_write_ha_state()

    async def async_added_to_hass(self):
        """Register required attributes and coordinator listener."""
        register_attr = []

        if ATTR_TEMPERATURE in self.meta:
            register_attr.append(
                self.meta[ATTR_TEMPERATURE]
            )

        if ATTR_CURRENT_TEMPERATURE in self.meta:
            register_attr.append(
                self.meta[ATTR_CURRENT_TEMPERATURE]
            )

        if ATTR_TARGET_TEMP_HIGH in self.meta:
            register_attr.append(
                self.meta[ATTR_TARGET_TEMP_HIGH]
            )

        if ATTR_TARGET_TEMP_LOW in self.meta:
            register_attr.append(
                self.meta[ATTR_TARGET_TEMP_LOW]
            )

        if ATTR_ENABLED in self.meta:
            register_attr.append(
                self.meta[ATTR_ENABLED]
            )

        self.coordinator.registerAttribute(register_attr)

        self.async_on_remove(
            self.coordinator.async_add_listener(
                self.async_write_ha_state
            )
        )

    async def async_update(self):
        """Update Thermia entity."""
        await self.coordinator.wantsRefresh(self.kind)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        writes = {}

        if ATTR_TARGET_TEMP_LOW in kwargs:
            writes[self.meta[ATTR_TARGET_TEMP_LOW]] = (
                kwargs[ATTR_TARGET_TEMP_LOW]
            )

        if ATTR_TARGET_TEMP_HIGH in kwargs:
            writes[self.meta[ATTR_TARGET_TEMP_HIGH]] = (
                kwargs[ATTR_TARGET_TEMP_HIGH]
            )

        if ATTR_TEMPERATURE in kwargs:
            writes[self.meta[ATTR_TEMPERATURE]] = (
                kwargs[ATTR_TEMPERATURE]
            )

        for reg, val in writes.items():
            await self.coordinator._async_set_data(
                reg,
                val,
            )
