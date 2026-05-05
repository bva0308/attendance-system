try:
    from .config import DeviceConfig
    from .models import SessionInfo, StudentInfo
    from .runtime import log, monotonic_ms, sleep_ms, ticks_diff
except ImportError:
    from config import DeviceConfig
    from models import SessionInfo, StudentInfo
    from runtime import log, monotonic_ms, sleep_ms, ticks_diff


class DeviceState:
    IDLE           = "IDLE"
    WAIT_QR        = "WAIT_QR"
    VERIFY_QR      = "VERIFY_QR"
    CAPTURE_FACE   = "CAPTURE_FACE"
    VERIFY_FACE    = "VERIFY_FACE"
    WAIT_FINGER    = "WAIT_FINGER"
    VERIFY_FINGER  = "VERIFY_FINGER"
    MARK_SUCCESS   = "MARK_SUCCESS"
    MARK_FAIL      = "MARK_FAIL"
    ERROR_RECOVERY = "ERROR_RECOVERY"


class CameraStateMachine:
    def __init__(self, camera_service, api_client, qr_service, storage_service, wifi,
                 fingerprint_service=None, relay_service=None):
        self.camera = camera_service
        self.api = api_client
        self.qr = qr_service
        self.storage = storage_service
        self.wifi = wifi
        self.fingerprint = fingerprint_service
        self.relay = relay_service

        self.state = DeviceState.IDLE
        self.message = "boot"
        self.active_session = SessionInfo()
        self.verified_session = SessionInfo()
        self.matched_student = StudentInfo()

        self.state_started_at = 0
        self.last_heartbeat_at = 0
        self.last_qr_attempt_at = 0
        self.last_face_attempt_at = 0

    def begin(self):
        self.transition(DeviceState.IDLE, "waiting for active session")

    def state_name(self):
        return self.state

    def last_message(self):
        return self.message

    def _reset_verification_context(self):
        self.verified_session = SessionInfo()
        self.matched_student = StudentInfo()

    def transition(self, next_state, next_message):
        previous_state = self.state
        if previous_state == next_state and self.message == next_message:
            return
        self.state = next_state
        self.message = next_message
        self.state_started_at = monotonic_ms()
        self.storage.save_last_state(self.state_name())
        if next_state in (DeviceState.MARK_FAIL, DeviceState.ERROR_RECOVERY):
            self.storage.save_last_error(next_message)
        log("state", "{0} -> {1} ({2})".format(previous_state, next_state, next_message))

    def do_heartbeat(self):
        if ticks_diff(monotonic_ms(), self.last_heartbeat_at) < DeviceConfig.HEARTBEAT_INTERVAL_MS:
            return
        self.last_heartbeat_at = monotonic_ms()
        ok, heartbeat_session, _pending_commands = self.api.post_heartbeat(self.state_name(), self.wifi.rssi())
        if ok:
            self.active_session = heartbeat_session
        else:
            self.active_session = SessionInfo()

    def _ready_state_for_active_session(self):
        if not self.active_session.valid:
            return DeviceState.IDLE, "no active session"
        if self.camera.ready():
            return DeviceState.WAIT_QR, "active session ready; present qr"
        return DeviceState.ERROR_RECOVERY, "camera unavailable"

    def tick(self):
        self.do_heartbeat()

        if not self.wifi.is_connected() and self.state != DeviceState.ERROR_RECOVERY:
            self._reset_verification_context()
            self.transition(DeviceState.ERROR_RECOVERY, "wifi disconnected")
            return

        if self.state == DeviceState.IDLE:
            next_state, message = self._ready_state_for_active_session()
            if next_state != DeviceState.IDLE or self.message != message:
                self.transition(next_state, message)
            return

        if self.state == DeviceState.WAIT_QR:
            if not self.active_session.valid:
                self._reset_verification_context()
                self.transition(DeviceState.IDLE, "no active session")
                return
            if ticks_diff(monotonic_ms(), self.last_qr_attempt_at) >= DeviceConfig.QR_SCAN_INTERVAL_MS:
                self.last_qr_attempt_at = monotonic_ms()
                qr_result, verified_session = self.qr.verify_session_qr()
                if qr_result.ok:
                    self.verified_session = verified_session
                    self.transition(DeviceState.CAPTURE_FACE, "qr verified; hold face in view")
                else:
                    self.transition(DeviceState.WAIT_QR, qr_result.message)
            return

        if self.state == DeviceState.CAPTURE_FACE:
            if ticks_diff(monotonic_ms(), self.state_started_at) < DeviceConfig.FACE_SETTLE_DELAY_MS:
                return
            self.transition(DeviceState.VERIFY_FACE, "verifying face")
            return

        if self.state == DeviceState.VERIFY_FACE:
            if ticks_diff(monotonic_ms(), self.last_face_attempt_at) < DeviceConfig.FACE_CAPTURE_DELAY_MS:
                return
            self.last_face_attempt_at = monotonic_ms()
            frame = self.camera.capture()
            if not frame:
                self.transition(DeviceState.VERIFY_FACE, "camera capture failed; keep face visible")
                return
            face_result, student = self.api.verify_face(frame, self.verified_session.token)
            self.camera.release(frame)
            if face_result.ok:
                self.matched_student = student
                self.transition(DeviceState.WAIT_FINGER, "face verified; place finger on sensor")
            else:
                self.transition(DeviceState.VERIFY_FACE, "{0}; keep face visible".format(face_result.message))
            return

        if self.state == DeviceState.WAIT_FINGER:
            if DeviceConfig.USE_EXTERNAL_FINGERPRINT_NODE:
                status, message = self.api.fingerprint_status(
                    self.verified_session.token,
                    self.matched_student.student_id,
                )
                if status == "completed":
                    self._reset_verification_context()
                    next_state, msg = self._ready_state_for_active_session()
                    self.transition(next_state, "fingerprint verified; ready for next student")
                    return
                if status == "failed":
                    self._reset_verification_context()
                    next_state, msg = self._ready_state_for_active_session()
                    self.transition(next_state, message or msg)
                    return
                self.transition(DeviceState.WAIT_FINGER, "face verified; use fingerprint device")
                sleep_ms(1000)
                return
            if ticks_diff(monotonic_ms(), self.state_started_at) < DeviceConfig.FINGERPRINT_SETTLE_DELAY_MS:
                return
            self.transition(DeviceState.VERIFY_FINGER, "reading fingerprint; keep finger on sensor")
            return

        if self.state == DeviceState.VERIFY_FINGER:
            if self.fingerprint is not None:
                fp_ok, fp_message = self.fingerprint.verify_template(
                    self.matched_student.fingerprint_template_id,
                    DeviceConfig.FINGERPRINT_TIMEOUT_MS,
                )
            else:
                fp_ok, fp_message = False, "fingerprint sensor not configured"
            if fp_ok:
                self.transition(DeviceState.MARK_SUCCESS, "all factors verified")
            else:
                self.transition(DeviceState.WAIT_FINGER, "{0}; place finger again".format(fp_message))
            return

        if self.state == DeviceState.MARK_SUCCESS:
            self.api.mark_attendance(
                self.verified_session.token,
                self.matched_student.student_id,
                by_qr=True,
                by_face=True,
                by_fingerprint=True,
            )
            if self.relay is not None:
                self.relay.pulse(DeviceConfig.RELAY_PULSE_MS)
            self._reset_verification_context()
            next_state, msg = self._ready_state_for_active_session()
            self.transition(next_state, msg)
            return

        if self.state == DeviceState.MARK_FAIL:
            self.api.log_verification_failure(
                self.verified_session.token,
                self.matched_student.student_id if self.matched_student.valid else None,
                status="face_or_fingerprint_mismatch",
                note=self.message,
            )
            sleep_ms(1200)
            self._reset_verification_context()
            next_state, msg = self._ready_state_for_active_session()
            self.transition(next_state, msg)
            return

        if self.state == DeviceState.ERROR_RECOVERY:
            if self.wifi.is_connected():
                next_state, message = self._ready_state_for_active_session()
                self.transition(next_state, message)
            else:
                sleep_ms(500)
            return
