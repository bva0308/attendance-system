"""
R307S / AS608 fingerprint sensor driver for MicroPython.
UART protocol: 57600 baud, UART2 on ESP32.
Packet format: [0xEF][0x01][addr:4][pid:1][len:2][data:n][checksum:2]
"""

try:
    from machine import UART
    import time as _time

    def _ticks_ms():
        return _time.ticks_ms()

    def _ticks_diff(a, b):
        return _time.ticks_diff(a, b)

    def _sleep_ms(ms):
        _time.sleep_ms(int(ms))

except ImportError:
    UART = None
    import time as _time

    def _ticks_ms():
        return int(_time.monotonic() * 1000)

    def _ticks_diff(a, b):
        return a - b

    def _sleep_ms(ms):
        _time.sleep(ms / 1000.0)


_CMD_GETIMAGE = 0x01
_CMD_IMG2TZ = 0x02
_CMD_SEARCH = 0x04
_CMD_REGMODEL = 0x05
_CMD_STORE = 0x06
_CMD_TEMPLATECOUNT = 0x1D

_PID_COMMAND = 0x01
_PID_ACK = 0x07

OK = 0
NOFINGER = 2
_TIMEOUT = 0xFF


class R307Sensor:
    def __init__(self, tx_pin, rx_pin, baudrate=57600, address=0xFFFFFFFF):
        self._tx_pin = tx_pin
        self._rx_pin = rx_pin
        self._baudrate = baudrate
        self._address = address
        self._uart = None
        self._matched_id = 0
        self._template_count = 0

    def connect(self):
        if UART is None:
            return False
        try:
            self._uart = UART(
                2,
                baudrate=self._baudrate,
                tx=self._tx_pin,
                rx=self._rx_pin,
                timeout=1000,
                timeout_char=100,
            )
            _sleep_ms(100)
            result = self._cmd(_CMD_TEMPLATECOUNT)
            return result == OK
        except Exception:
            return False

    # ------------------------------------------------------------------ helpers

    def _build_packet(self, data_bytes):
        length = len(data_bytes) + 2  # +2 for checksum
        addr = self._address
        packet = bytearray([
            0xEF, 0x01,
            (addr >> 24) & 0xFF,
            (addr >> 16) & 0xFF,
            (addr >> 8) & 0xFF,
            addr & 0xFF,
            _PID_COMMAND,
            (length >> 8) & 0xFF,
            length & 0xFF,
        ])
        for b in data_bytes:
            packet.append(b)
        checksum = _PID_COMMAND + (length >> 8) + (length & 0xFF)
        for b in data_bytes:
            checksum += b
        packet.append((checksum >> 8) & 0xFF)
        packet.append(checksum & 0xFF)
        return packet

    def _read_response(self, timeout_ms=3000):
        """Return (confirm_code, extra_bytes) or (_TIMEOUT, b'')."""
        buf = bytearray()
        start = _ticks_ms()
        while _ticks_diff(_ticks_ms(), start) < timeout_ms:
            waiting = self._uart.any() if self._uart else 0
            if waiting:
                buf += self._uart.read(waiting)
            # scan for 0xEF 0x01 header
            i = 0
            while i < len(buf) - 1:
                if buf[i] == 0xEF and buf[i + 1] == 0x01:
                    break
                i += 1
            else:
                _sleep_ms(10)
                continue

            # need at least: header(2)+addr(4)+pid(1)+len(2) = 9 bytes from i
            if len(buf) - i < 9:
                _sleep_ms(10)
                continue

            pkt_len = (buf[i + 7] << 8) | buf[i + 8]
            total = i + 9 + pkt_len  # 9 fixed bytes + pkt_len (data + checksum)
            if len(buf) < total:
                _sleep_ms(10)
                continue

            confirm = buf[i + 9]
            extra = bytes(buf[i + 10: i + 9 + pkt_len - 2])  # strip checksum
            return confirm, extra

        return _TIMEOUT, b""

    def _cmd(self, command, params=()):
        if self._uart is None:
            return _TIMEOUT
        data = bytearray([command]) + bytearray(params)
        self._uart.write(self._build_packet(data))
        code, _ = self._read_response()
        return code

    # --------------------------------------------------------- public interface

    def get_image(self):
        return self._cmd(_CMD_GETIMAGE)

    def image_to_template(self, slot_id):
        return self._cmd(_CMD_IMG2TZ, [slot_id & 0xFF])

    def fast_search(self):
        """Search buffer-1 against entire library (pages 0–127)."""
        if self._uart is None:
            return _TIMEOUT
        data = bytearray([_CMD_SEARCH, 0x01, 0x00, 0x00, 0x00, 0x7F])
        self._uart.write(self._build_packet(data))
        code, extra = self._read_response()
        if code == OK and len(extra) >= 2:
            self._matched_id = (extra[0] << 8) | extra[1]
        return code

    def get_matched_template_id(self):
        return self._matched_id

    def get_template_count(self):
        if self._uart is None:
            return 0
        data = bytearray([_CMD_TEMPLATECOUNT])
        self._uart.write(self._build_packet(data))
        code, extra = self._read_response()
        if code == OK and len(extra) >= 2:
            self._template_count = (extra[0] << 8) | extra[1]
        return self._template_count

    def create_model(self):
        return self._cmd(_CMD_REGMODEL)

    def store_model(self, template_id):
        return self._cmd(_CMD_STORE, [0x01, (template_id >> 8) & 0xFF, template_id & 0xFF])
