from r307s import R307Sensor

sensor = R307Sensor(tx_pin=17, rx_pin=16)
if sensor.connect():
    print("OK tx=17 rx=16, templates: " + str(sensor.get_template_count()))
else:
    print("FAIL tx=17 rx=16")
