# Wiring

## Active Firmware Pin Map

The current MicroPython firmware uses UART2 for the R307 link and expects the wiring below.
Development mode assumes a stable 5V USB supply shared by the ESP32 board, R307, and relay module.

| Module | Pin | Connect To | Notes |
|---|---|---|---|
| ESP32 board | VIN / 5V | Stable 5V USB supply | Required for reliable bring-up |
| ESP32 board | GND | Common ground | Share with R307 and relay |
| R307 | VCC | VIN / 5V | Most R307 boards expect 5V power |
| R307 | GND | GND | Common ground required |
| R307 | TX | GPIO16 | Sensor sends data into ESP32 RX2 |
| R307 | RX | GPIO17 | ESP32 TX2 sends commands to sensor |
| R307 | Pins 5 and 6 | Not connected | Optional lines, safe to leave open for this project |
| Relay module | VCC | 5V | Do not power relay coil from weak 3.3V rail |
| Relay module | GND | GND | Common ground required |
| Relay module | IN | GPIO13 | Active during successful attendance mark |

## UART Notes

- The code now names these pins explicitly as `R307_UART_RX_PIN = 16` and `R307_UART_TX_PIN = 17` to match the actual ESP32 UART direction.
- This means the sensor's `TX` wire must land on the ESP32 receive pin `GPIO16`.
- The sensor's `RX` wire must land on the ESP32 transmit pin `GPIO17`.
- Older notes that described `GPIO14/GPIO15` are no longer the source of truth for this repo.

## Flashing Rule While Debugging Sensor Wiring

The sensor should not block normal UART flashing because it is no longer on `U0R/U0T`, but unstable breadboard wiring can still drag the board down.

If `esptool` stalls or the erase fails mid-transfer:

1. Unplug all four R307 wires from the ESP32 or breadboard.
2. Hold `BOOT`, tap `EN`, then release `BOOT` after the board enters download mode.
3. Flash or erase the ESP32 with only USB power connected.
4. Reconnect `VCC`, `GND`, `TX -> GPIO16`, and `RX -> GPIO17`.
5. Boot again and check serial logs for `[finger] sensor online` or `[finger] sensor not detected`.

## Board-Level Cautions

- Avoid `GPIO0`, `GPIO2`, and `GPIO12` for the fingerprint sensor because they are boot-sensitive strapping pins.
- Keep the relay off the same signal pins used for UART or flashing.
- If you are using an ESP32-CAM variant with PSRAM tied to `GPIO16/GPIO17`, you may need a different board or a different fingerprint UART mapping. The active project code assumes these pins are available.

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
