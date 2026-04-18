# Wiring

## Final Recommended Wiring Table

Development mode assumes a stable 5V USB supply to the ESP32-CAM and relay module.

| Module | Pin | Connect To | Notes |
|---|---|---|---|
| ESP32-CAM | 5V | Stable 5V USB supply | Required for first working prototype |
| ESP32-CAM | GND | Common ground | Share with R307 and relay |
| R307 | VCC | 5V | Check your module label; many R307 modules accept 3.6V to 6V |
| R307 | GND | GND | Common ground required |
| R307 | TX | GPIO14 | ESP32 receives sensor data here |
| R307 | RX | GPIO15 | ESP32 transmits commands here |
| Relay module | VCC | 5V | Do not power relay coil from weak 3.3V rail |
| Relay module | GND | GND | Common ground required |
| Relay module | IN | GPIO13 | Chosen to avoid camera and upload UART |

## Why These Pins Were Chosen

- Camera pins are fixed by the AI Thinker board and already occupy most GPIOs.
- `GPIO1` and `GPIO3` are reserved for flashing and serial monitor, so they were intentionally avoided for the fingerprint sensor.
- `GPIO14` and `GPIO15` are available when microSD is not used, making them a practical remapped UART pair for the R307.
- `GPIO13` is used for the relay because it does not conflict with the camera and is safer than forcing the relay onto `GPIO0`, `GPIO2`, or upload UART pins.

## Important ESP32-CAM Notes

- Do not use microSD in this prototype with the chosen pin map.
- `GPIO16` and `GPIO17` are not offered as free pins because the ESP32-CAM module commonly uses them internally for PSRAM.
- `GPIO12` is avoided because it is a strapping pin and can break boot if pulled incorrectly.
- `GPIO0` is the flash boot pin and must stay available for uploads.

## Upload-Time Rule

With the recommended mapping, fingerprint wiring does not need to be disconnected for normal flashing because it is not on `U0R/U0T`.

Still, if you see unstable boot or upload behavior:

1. Disconnect relay `IN` from `GPIO13`.
2. Leave R307 connected.
3. Put `GPIO0` to GND.
4. Flash.
5. Reconnect relay input if needed.

## Safer Alternative Pin Profile

If your relay module causes boot instability on `GPIO13` because of its input circuit:

- Keep R307 on `GPIO14/GPIO15`
- Add a transistor buffer stage between `GPIO13` and relay input
- Or move relay input to `GPIO2` only as a last resort and only after boot testing, because `GPIO2` is also a sensitive boot-related line on ESP32-CAM boards

## Power Design

### Mode A: Development Mode

- Recommended and fully supported
- ESP32-CAM powered from stable 5V USB source
- Relay powered from same 5V source
- R307 powered from same regulated rail

### Mode B: Battery Mode

Using only:

- 1x 18650 cell
- 1x TP4056 charger module

is not a stable full standalone solution for this prototype.

Reason:

- TP4056 charges the cell and may provide protected battery output
- It does not boost 3.7V battery voltage to a stable 5V rail for ESP32-CAM + R307 + relay
- Relay coil current spikes and ESP32-CAM camera current bursts can cause brownouts

Recommended extras for real standalone battery mode:

- 5V boost converter
- Power switch
- Large decoupling capacitor near ESP32-CAM, such as 470uF to 1000uF
