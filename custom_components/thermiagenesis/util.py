"""Helpers shared by the ThermiaGenesis platforms."""
from .const import ATTR_UNIT
from .const import UNIT_TEMPERATURE

# Genesis firmware reports this exact value on a temperature input whose sensor
# is not fitted or not connected.
#
# It is a *scaled* sentinel, not a raw one: on a Calibra Cool 7 BW every
# unpopulated circuit reads it, across registers with different scale factors --
# the room temperature sensor (register 121, scale 10) transmits 2000 while the
# system supply line, HGW, pool, TWC and mix valve 1-5 sensors (scale 100)
# transmit 20000. Both resolve to 200.0 degrees, which no sensor on a heat pump
# can legitimately measure.
NOT_CONNECTED_TEMPERATURE = 200.0


def temperature_or_none(value):
    """Return None when a temperature register reports a disconnected sensor.

    Anything that is not a number is passed through untouched.
    """
    if value is None:
        return None

    try:
        if float(value) == NOT_CONNECTED_TEMPERATURE:
            return None
    except (TypeError, ValueError):
        return value

    return value


def is_temperature(meta):
    """Return True when a SENSOR_TYPES entry describes a temperature."""
    return meta.get(ATTR_UNIT) == UNIT_TEMPERATURE
