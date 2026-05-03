import serial
import time
import sys

PORT = "COM9"
BAUD = 115200

# Read local files to upload
with open(r"firmware\esp32_cam_attendance\pins.py", "rb") as f:
    pins_content = f.read()

with open(r"firmware\esp32_cam_attendance\r307s.py", "rb") as f:
    r307s_content = f.read()

def make_write_code(filename, content):
    escaped = content.replace(b"\\", b"\\\\").replace(b"'", b"\\'").replace(b"\n", b"\\n").replace(b"\r", b"")
    return b"f=open('" + filename.encode() + b"','wb');f.write(b'" + escaped + b"');f.close();print('WROTE " + filename.encode() + b"')\n\x04"

with serial.Serial(PORT, BAUD, timeout=1) as s:
    s.setRTS(True)
    time.sleep(0.1)
    s.setRTS(False)
    time.sleep(0.8)
    s.read_all()

    for attempt in range(20):
        s.write(b"\x03\x03")
        time.sleep(0.15)
        s.write(b"\x01")
        time.sleep(0.35)
        resp = s.read_all()
        if b"raw REPL" in resp or b"OK" in resp:
            print("REPL entered on attempt {}".format(attempt + 1))

            # Write pins.py
            s.write(make_write_code("pins.py", pins_content))
            time.sleep(3)
            out = s.read_all()
            print("pins.py:", "OK" if b"WROTE" in out else "FAIL - " + repr(out[:100]))

            # Write r307s.py
            time.sleep(0.5)
            s.write(make_write_code("r307s.py", r307s_content))
            time.sleep(4)
            out = s.read_all()
            print("r307s.py:", "OK" if b"WROTE" in out else "FAIL - " + repr(out[:100]))
            break
        print("[{}]".format(attempt + 1))
    else:
        print("could not enter REPL")
