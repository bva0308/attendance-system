try:
    from .runtime import log, monotonic_ms, sleep_ms, ticks_diff
    from .pins import Pins
    from .r307s import R307Sensor
except ImportError:
    from runtime import log, monotonic_ms, sleep_ms, ticks_diff
    from pins import Pins
    from r307s import R307Sensor


FINGERPRINT_OK = 0
FINGERPRINT_NOFINGER = 2


class NullFingerprintSensor:
    def connect(self):
        return False

    def get_image(self):
        return FINGERPRINT_NOFINGER

    def image_to_template(self, slot_id):
        return FINGERPRINT_OK

    def fast_search(self):
        return FINGERPRINT_OK

    def get_matched_template_id(self):
        return 0

    def get_template_count(self):
        return 0

    def create_model(self):
        return FINGERPRINT_OK

    def store_model(self, template_id):
        return FINGERPRINT_OK


class FingerprintService:
    def __init__(self, sensor=None):
        if sensor is None:
            sensor = R307Sensor(tx_pin=Pins.R307_UART_TX_PIN, rx_pin=Pins.R307_UART_RX_PIN)
        self.sensor = sensor
        self.ready = False

    def begin(self):
        self.ready = bool(self.sensor.connect())
        log("finger", "sensor online" if self.ready else "sensor not detected")
        return self.ready

    def sensor_ready(self):
        return self.ready

    def _wait_for_finger_image(self, timeout_ms):
        started_at = monotonic_ms()
        while ticks_diff(monotonic_ms(), started_at) < timeout_ms:
            code = self.sensor.get_image()
            if code == FINGERPRINT_OK:
                return True, "finger image captured"
            if code != FINGERPRINT_NOFINGER:
                return False, "sensor image capture error"
            sleep_ms(120)
        return False, "fingerprint timeout"

    def verify_template(self, expected_template_id, timeout_ms):
        if not self.ready:
            return False, "fingerprint sensor unavailable"
        if expected_template_id == 0:
            return False, "student has no fingerprint template"

        ok, message = self._wait_for_finger_image(timeout_ms)
        if not ok:
            return False, message
        if self.sensor.image_to_template(1) != FINGERPRINT_OK:
            return False, "failed to convert fingerprint image"
        if self.sensor.fast_search() != FINGERPRINT_OK:
            return False, "fingerprint not recognized"
        if self.sensor.get_matched_template_id() != expected_template_id:
            return False, "wrong finger for matched student"
        return True, "fingerprint matched"

    def identify_template(self, timeout_ms):
        if not self.ready:
            return False, 0, "fingerprint sensor unavailable"

        ok, message = self._wait_for_finger_image(timeout_ms)
        if not ok:
            return False, 0, message
        if self.sensor.image_to_template(1) != FINGERPRINT_OK:
            return False, 0, "failed to convert fingerprint image"
        if self.sensor.fast_search() != FINGERPRINT_OK:
            return False, 0, "fingerprint not recognized"

        template_id = int(self.sensor.get_matched_template_id() or 0)
        if template_id <= 0:
            return False, 0, "fingerprint template not registered"
        return True, template_id, "fingerprint matched"

    def enroll_next_template(self):
        if not self.ready:
            return False, 0, "fingerprint sensor unavailable"

        assigned_template_id = int(self.sensor.get_template_count()) + 1
        if assigned_template_id == 0 or assigned_template_id > 127:
            return False, 0, "sensor template storage full"

        log("finger", "place finger for first scan")
        ok, message = self._wait_for_finger_image(15000)
        if not ok:
            return False, 0, message
        if self.sensor.image_to_template(1) != FINGERPRINT_OK:
            return False, 0, "first scan conversion failed"

        log("finger", "remove finger")
        sleep_ms(2000)
        while self.sensor.get_image() != FINGERPRINT_NOFINGER:
            sleep_ms(100)

        log("finger", "place same finger again")
        ok, message = self._wait_for_finger_image(15000)
        if not ok:
            return False, 0, message
        if self.sensor.image_to_template(2) != FINGERPRINT_OK:
            return False, 0, "second scan conversion failed"
        if self.sensor.create_model() != FINGERPRINT_OK:
            return False, 0, "fingerprints did not match closely enough"
        if self.sensor.store_model(assigned_template_id) != FINGERPRINT_OK:
            return False, 0, "failed to store fingerprint template"
        return True, assigned_template_id, "fingerprint enrolled"
