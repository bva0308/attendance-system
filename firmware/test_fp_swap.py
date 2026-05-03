from r307s import R307Sensor

sensor = R307Sensor(tx_pin=16, rx_pin=15)
if sensor.connect():
    print("OK tx=16 rx=15, templates: " + str(sensor.get_template_count()))
else:
    print("FAIL tx=16 rx=15")
