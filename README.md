# GCBASIC Temperature Sensor for Home Assistant

A Home Assistant custom integration that reads a temperature reading from a
GC-BASIC device over a USB/serial connection (e.g. `/dev/ttyACM0`) which is a CDC/USB connnection.

The device is request/response: it only sends a reading after receiving a
query character (default `t`). Home Assistant's built-in `serial` platform
only listens passively and can't drive that protocol, so this integration
sends the query itself on every poll and reads back all lines the device
sends. Any line starting with `+` or `-` is treated as the temperature
(e.g. `+23.5`); everything else is ignored.

### Glitch management

The device occasionally returns a garbled reading — most often `0.00`, but
it can land on any stray value. Reporting that straight to Home Assistant
would show a false spike/drop in history and any automations or graphs
watching the sensor.

To filter this out, the integration keeps a short rolling history of raw
readings. A new reading is only trusted immediately if it's close to the
last trusted value. If it jumps further away than that, it's treated as a
suspected glitch **unless** the last several raw readings were already
trending toward it — in which case it's accepted as a genuine, fast change
rather than a glitch. A rejected glitch is replaced with the last trusted
reading instead of being reported to Home Assistant.

This is tuned via three optional config options — see
[Configuration](#configuration) below — so it can be loosened or tightened
per device depending on how "twitchy" it is and how fast its real
temperature can change.

## Requirements

- A GC-BASIC device connected via USB serial that responds to a query
  character with one or more lines of text, at least one of which starts
  with `+` or `-` and is a valid number.
- [HACS](https://hacs.xyz/) installed in your Home Assistant instance.

## Installation via HACS

This integration is not in the default HACS store, so add it as a custom
repository:

1. In Home Assistant, go to **HACS → Integrations**.
2. Click the three-dot menu (top right) → **Custom repositories**.
3. Add repository URL:
   `https://github.com/GreatCowBASIC/ha-GCBASIC-Temperature_Solution`
4. Category: **Integration**.
5. Click **Add**.
6. Search HACS for **GCBASIC Temperature Sensor** and click **Download**.
7. Restart Home Assistant.

## Manual installation (alternative to HACS)

Copy the `custom_components/gcbasic_temp` folder from this repository into
your Home Assistant `config/custom_components/` directory, then restart
Home Assistant.

## Configuration

This integration is configured via YAML (no config flow / UI setup yet).
Add it under `sensor:` in `configuration.yaml`:

```yaml
sensor:
  - platform: gcbasic_temp
    serial_port: /dev/ttyACM0
    baudrate: 9600          # match your GC-BASIC firmware's baud rate
    query_char: "t"         # the character your firmware expects to trigger a reply
    name: "GCBASIC Temperature"
    scan_interval: 30       # optional, seconds between queries (default: 30)
    glitch_window: 5        # optional, see "Glitch management" above (default: 5)
    glitch_jump: 3.0        # optional, °C jump that looks suspicious (default: 3.0)
    glitch_band: 1.0        # optional, °C tolerance for trend confirmation (default: 1.0)
```

| Option           | Default | Meaning                                                                                                    |
| ----------------- | ------- | ----------------------------------------------------------------------------------------------------------- |
| `glitch_window`   | `5`     | How many of the most recent raw readings must already be near a new value before a big jump is trusted.    |
| `glitch_jump`     | `3.0`   | A reading that differs from the last trusted value by more than this (°C) is treated as a suspected glitch. |
| `glitch_band`     | `1.0`   | How close (°C) each of the `glitch_window` recent readings must be to the new value to confirm a real trend. |

### Finding your serial port

In Home Assistant: **Settings → System → Hardware → All Hardware**, or via
SSH/Terminal add-on: `ls -l /dev/serial/by-id/`. A `by-id` path is more
stable than `/dev/ttyACM0`, which can shift if other USB-serial devices are
plugged in.

## Troubleshooting

Check **Settings → System → Logs**, filtered to `gcbasic_temp`:

- `No response from <port> within timeout` — the device didn't reply at
  all; check baud rate and wiring.
- `No temperature line (starting with '+' or '-') from <port>. Raw
  response: [...]` — the device replied, but none of the lines looked like
  a temperature reading. The raw response is logged so you can see what it
  actually sent (useful for finding the right `query_char` too — try `?`
  to get the device's help text).
- `Could not parse temperature line '...' from <port>` — a line started
  with `+`/`-` but wasn't a valid number.

## License

MIT — see [LICENSE](LICENSE).
