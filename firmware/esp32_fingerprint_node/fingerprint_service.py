from config import DeviceConfig
from r307s import R307Sensor
from runtime import log, monotonic_ms, sleep_ms, ticks_diff


FINGERPRINT_OK = 0
FINGERPRINT_NOFINGER = 2


class FingerprintService:
    def __init__(self):
        self.sensor = R307Sensor(
            tx_pin=DeviceConfig.R307_UART_TX_PIN,
            rx_pin=DeviceConfig.R307_UART_RX_PIN,
        )
        self.ready = False

    def begin(self):
        self.ready = bool(self.sensor.connect())
        log("finger", "R307S online" if self.ready else "R307S not detected")
        return self.ready

    def _ensure_ready(self):
        return self.ready or self.begin()

    def _wait_for_finger_image(self, timeout_ms):
        started_at = monotonic_ms()
        while ticks_diff(monotonic_ms(), started_at) < timeout_ms:
            code = self.sensor.get_image()
            if code == FINGERPRINT_OK:
                return True, "finger image captured"
            if code != FINGERPRINT_NOFINGER:
                return False, "sensor image capture error code {0}".format(code)
            sleep_ms(120)
        return False, "fingerprint timeout"

    def enroll_next_template(self):
        if not self._ensure_ready():
            return False, 0, "fingerprint sensor unavailable"

        template_id = int(self.sensor.get_template_count()) + 1
        if template_id <= 0 or template_id > 127:
            return False, 0, "sensor template storage full"

        log("finger", "place finger for first scan")
        ok, message = self._wait_for_finger_image(15000)
        if not ok:
            return False, 0, message
        if self.sensor.image_to_template(1) != FINGERPRINT_OK:
            return False, 0, "first scan conversion failed"

        log("finger", "remove finger")
        sleep_ms(2000)
        started_at = monotonic_ms()
        while ticks_diff(monotonic_ms(), started_at) < 8000:
            code = self.sensor.get_image()
            if code == FINGERPRINT_NOFINGER:
                break
            sleep_ms(150)
        else:
            return False, 0, "finger was not removed between scans"

        log("finger", "place same finger again")
        ok, message = self._wait_for_finger_image(15000)
        if not ok:
            return False, 0, message
        if self.sensor.image_to_template(2) != FINGERPRINT_OK:
            return False, 0, "second scan conversion failed"
        if self.sensor.create_model() != FINGERPRINT_OK:
            return False, 0, "fingerprints did not match"
        if self.sensor.store_model(template_id) != FINGERPRINT_OK:
            return False, 0, "failed to store template"

        return True, template_id, "fingerprint enrolled"

    def verify_expected_template(self, expected_template_id, timeout_ms):
        if not self._ensure_ready():
            return False, 0, "fingerprint sensor unavailable"
        expected_template_id = int(expected_template_id or 0)
        if expected_template_id <= 0:
            return False, 0, "student has no fingerprint template"

        ok, message = self._wait_for_finger_image(timeout_ms)
        if not ok:
            return False, 0, message
        if self.sensor.image_to_template(1) != FINGERPRINT_OK:
            return False, 0, "failed to convert fingerprint image"
        if self.sensor.fast_search() != FINGERPRINT_OK:
            return False, 0, "fingerprint not recognized"

        matched_id = int(self.sensor.get_matched_template_id() or 0)
        if matched_id != expected_template_id:
            return False, matched_id, "wrong finger: matched template {0}".format(matched_id)
        return True, matched_id, "fingerprint matched"
