from machine import UART
import time

pairs = [(12, 14), (14, 12), (1, 3), (4, 2)]
for tx, rx in pairs:
    try:
        u = UART(1, baudrate=57600, tx=tx, rx=rx, timeout=500)
        time.sleep_ms(100)
        print("UART(1) tx={} rx={} OK".format(tx, rx))
        u.deinit()
    except Exception as e:
        print("UART(1) tx={} rx={} FAIL: {}".format(tx, rx, e))
