from r307s import R307Sensor
import time

TX_PIN = 15
RX_PIN = 16

print("Connecting to R307S on TX={} RX={}...".format(TX_PIN, RX_PIN))
sensor = R307Sensor(tx_pin=TX_PIN, rx_pin=RX_PIN)

if sensor.connect():
    count = sensor.get_template_count()
    print("OK - sensor online. Stored templates: {}".format(count))
else:
    print("FAIL - sensor not detected. Check wiring (try swapping TX/RX pins).")
    raise SystemExit

print("Place a finger on the sensor (5 seconds)...")
deadline = time.ticks_add(time.ticks_ms(), 5000)
detected = False
while time.ticks_diff(deadline, time.ticks_ms()) > 0:
    code = sensor.get_image()
    if code == 0:
        print("Finger detected!")
        detected = True
        break
    elif code == 2:
        pass
    else:
        print("Sensor error code: {}".format(code))
        break
    time.sleep_ms(120)

if not detected:
    print("No finger detected in 5 seconds.")
