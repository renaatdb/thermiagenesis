# Thermia Genesis – Calibra Cool fork

[![GitHub Activity](https://img.shields.io/github/commit-activity/y/renaatdb/thermiagenesis.svg?style=for-the-badge)](https://github.com/renaatdb/thermiagenesis/commits/calibra-cool)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://hacs.xyz)

Home Assistant custom integration for Thermia heat pumps using **local Modbus TCP**.

This repository is a fork of
[CJNE/thermiagenesis](https://github.com/CJNE/thermiagenesis)
with additional fixes and functionality tested on a:

**Thermia Calibra Cool 7 BW**

> [!IMPORTANT]
> This fork is currently tested on a **Thermia Calibra Cool 7 BW**.
>
> Other Thermia Genesis inverter models may work, but the Calibra-specific
> additions have not yet been verified on other models.

## Why this fork exists

The original Thermia Genesis integration already exposes many Modbus registers
to Home Assistant.

On the Calibra Cool 7 BW, however, some functions are not represented correctly
by the generic inverter implementation.

This fork currently focuses on:

- reliable detection of actual **passive cooling**;
- exposing the **tap-water directional valve position**;
- improved Calibra Cool device information in Home Assistant;
- Home Assistant **long-term statistics** for supported Thermia sensors;
- filtering invalid **200 °C values from disconnected temperature sensors**;
- improved Home Assistant frontend compatibility and icon handling;
- retaining compatibility with existing Home Assistant device registrations;
- local communication with the heat pump using Modbus TCP.

## Calibra Cool improvements

### Reliable passive cooling detection

On the tested Calibra Cool 7 BW, the original Genesis discrete input:

`Mixing Valve 1 Is Producing Passive Cooling`

does not reliably represent whether passive cooling is actually running.

This fork therefore adds a new read-only binary sensor:

**Passive Cooling Active**

Passive cooling is considered active when:

- `Mix Valve Cooling Opening Degree` is greater than 0%;
- `Compressor Speed Rpm` is exactly 0 rpm.

Both real Modbus values must be available.

Missing values are deliberately **not interpreted as zero**, preventing false
passive-cooling detections.

The main `Heatpump` entity also reports:

`Passive Cooling`

when these conditions are met, even if the native Genesis heat-pump state still
reports `OFF`.

### Tap-water directional valve position

This fork adds:

**Tap Water Valve Position**

The value is shown as a percentage.

The underlying register is already known by `pythermiagenesis`, but it is
filtered out by the generic inverter model used by the upstream integration.

This fork registers the value explicitly for the tested Calibra installation.

### Device information

The device is displayed in Home Assistant as:

- Manufacturer: **Thermia**
- Model: **Calibra Cool 7 BW**

The original internal Home Assistant device identifier is intentionally kept.

This prevents an existing installation from creating a second heat-pump device
when upgrading from the upstream Thermia Genesis integration.

### Home Assistant sensor improvements

This fork also includes several Home Assistant compatibility and data-quality
improvements tested on a Thermia Calibra Cool 7 BW.

#### Long-term statistics

Thermia sensor entities use Home Assistant's `SensorEntity` model with
appropriate `device_class` and `state_class` values.

This enables Home Assistant long-term statistics for supported measurements
such as:

- temperatures;
- electrical power and energy;
- pump and valve percentages;
- operating hours.

Text-based status sensors are deliberately excluded from statistics.

#### Disconnected temperature sensors

Thermia Genesis reports exactly `200 °C` for several temperature inputs when
the corresponding physical sensor is not fitted.

This fork recognises that value as a disconnected-sensor sentinel and reports
the entity as:

`unknown`

instead of recording an incorrect 200 °C measurement.

Real temperature measurements are left unchanged.

This also prevents an optional missing room-temperature sensor from appearing
as a false 200 °C current temperature in Home Assistant.

#### Home Assistant frontend fixes

Several Home Assistant compatibility issues have also been corrected:

- removed an unresolved `{model}` placeholder from the integration title;
- corrected Material Design icon identifiers such as `mdi-gauge` to the valid
  `mdi:gauge` format;
- improved sensor units and classifications where applicable.

These changes improve Home Assistant logs, entity presentation and recorder
statistics.

## Useful entities

Some particularly useful entities on the tested Calibra Cool 7 BW are:

- `Heatpump`
- `Enable Passive Cooling`
- `Passive Cooling Active`
- `Mix Valve Cooling Opening Degree`
- `Compressor Speed Rpm`
- `Compressor Speed Percent`
- `Brine In Temperature`
- `Brine Out Temperature`
- `Brine Circulation Pump Speed`
- `Condenser In Temperature`
- `Condenser Out Temperature`
- `Condenser Circulation Pump Speed`
- `Outdoor Temperature`
- `Tap Water Top Temperature`
- `Tap Water Lower Temperature`
- `Tap Water Weighted Temperature`
- `Tap Water Valve Position`

Thermia Genesis exposes many more entities.

Not every register is useful or valid for every Thermia model, so many entities
are disabled by default.

## Installation with HACS

This repository can be installed as a **custom HACS repository**.

1. Open HACS in Home Assistant.
2. Open the custom repositories menu.
3. Add:

   `https://github.com/renaatdb/thermiagenesis`

4. Select **Integration** as repository type.
5. Install **Thermia Genesis - Calibra Cool**.
6. Restart Home Assistant.
7. Go to **Settings → Devices & services → Add integration**.
8. Search for **Thermia Genesis**.
9. Configure the Modbus TCP connection to the heat pump.

The default branch of this fork is:

`calibra-cool`

## Manual installation

Copy the complete directory:

```text
custom_components/thermiagenesis/
```

to the `custom_components` directory of your Home Assistant configuration.

Your Home Assistant configuration should then contain:

```text
/config/custom_components/thermiagenesis/
```

Restart Home Assistant and add **Thermia Genesis** from:

**Settings → Devices & services → Add integration**

Configure the local Modbus TCP connection to the Thermia heat pump.

## Contributions

Community improvements, testing and pull requests are welcome.

Special thanks to
[@bolkedebruin](https://github.com/bolkedebruin)
for contributions improving:

- Home Assistant long-term statistics;
- handling of disconnected temperature sensors;
- Home Assistant translation/frontend compatibility;
- Material Design icon identifiers;
- sensor units and classifications.

These contributions were tested on a Thermia Calibra Cool 7 BW and have helped
make this fork more reliable and more useful to other Home Assistant users.

## Credits

This repository is based on the original
[CJNE/thermiagenesis](https://github.com/CJNE/thermiagenesis)
Home Assistant integration.

The original project, its authors and contributors remain the foundation of
this fork.

The underlying Modbus communication uses
[`pythermiagenesis`](https://github.com/CJNE/pythermiagenesis).

## License

This fork retains the license of the original Thermia Genesis project.

See [LICENSE](LICENSE) for details.
