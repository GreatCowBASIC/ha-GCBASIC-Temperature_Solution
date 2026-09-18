"""Constants for the CDC USB Terminal integration.

Wire protocol reference (shared by the WPF/Avalonia desktop apps in the
CDC_Terminal repo and this integration): single ASCII characters, no
required framing.

    '?'         probe (used for autoconnect, does not change device state)
    '1'..'4'    toggle LED 1-4
    'a'         all LEDs on
    'z'         all LEDs off
    'x'         query LED + potentiometer state -> "LEDn=ON/OFF", "ADC=nnn"
    't'         query temperature -> "TEMP=xx.x" or a bare "+dd.d"/"-dd.d"
"""
from __future__ import annotations

DOMAIN = "cdc_usb"

CONF_BAUD_RATE = "baud_rate"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_TEMP_ADJUSTMENT = "temp_adjustment"
CONF_GLITCH_WINDOW = "glitch_window"
CONF_GLITCH_JUMP = "glitch_jump"
CONF_GLITCH_BAND = "glitch_band"

DEFAULT_BAUD_RATE = 9600
# Both desktop apps poll t/x every 60s while "Data Logging" is active.
DEFAULT_SCAN_INTERVAL = 60
DEFAULT_TEMP_ADJUSTMENT = -0.10
# Same defaults as the older gcbasic_temp YAML sensor this integration
# supersedes, so behaviour doesn't change for anyone porting over from it.
DEFAULT_GLITCH_WINDOW = 5
DEFAULT_GLITCH_JUMP = 3.0
DEFAULT_GLITCH_BAND = 1.0

# Small settle time between writing a command and reading the device's
# reply back out of the shared client state, before pushing it to entities.
REPLY_SETTLE_SECONDS = 0.3

CMD_PROBE = "?"
CMD_QUERY_TEMP = "t"
CMD_QUERY_STATUS = "x"
CMD_ALL_ON = "a"
CMD_ALL_OFF = "z"

LED_NUMBERS = (1, 2, 3, 4)
LED_COMMANDS = {led: str(led) for led in LED_NUMBERS}
