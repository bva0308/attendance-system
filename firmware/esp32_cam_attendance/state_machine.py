try:
    from .config import DeviceConfig
    from .models import SessionInfo, StudentInfo
    from .runtime import log, monotonic_ms, sleep_ms, ticks_diff
except ImportError:
    from config import DeviceConfig
    from models import SessionInfo, StudentInfo
    from runtime import log, monotonic_ms, sleep_ms, ticks_diff


class DeviceState:
    IDLE = "IDLE"
    WAIT_QR = "WAIT_QR"
    VERIFY_QR = "VERIFY_QR"
    CAPTURE_FACE = "CAPTURE_FACE"
    VERIFY_FACE = "VERIFY_FACE"
    FACE_VERIFIED = "FACE_VERIFIED"
    MARK_FAIL = "MARK_FAIL"
    ERROR_RECOVERY = "ERROR_RECOVERY"


class CameraStateMachine:
    def __init__(self, camera_service, api_client, qr_service, storage_service, wifi):
        self.camera = camera_service
        self.api = api_client
        self.qr = qr_service
        self.storage = storage_service
        self.wifi = wifi

        self.state = DeviceState.IDLE
        self.message = "boot"
        self.active_session = SessionInfo()
        self.verified_session = SessionInfo()
        self.matched_student = StudentInfo()

        self.state_started_at = 0
        self.last_heartbeat_at = 0
        self.last_qr_attempt_at = 0

    def begin(self):
        self.transition(DeviceState.IDLE, "camera-only device waiting for active session")

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

        if (
            self.state in (DeviceState.CAPTURE_FACE, DeviceState.VERIFY_FACE, DeviceState.FACE_VERIFIED)
            and ticks_diff(monotonic_ms(), self.state_started_at) >= DeviceConfig.STATE_TIMEOUT_MS
        ):
            self.transition(DeviceState.MARK_FAIL, "camera verification timeout")
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
                self.transition(DeviceState.VERIFY_QR, "capturing qr frame")
            return

        if self.state == DeviceState.VERIFY_QR:
            qr_result, verified_session = self.qr.verify_session_qr()
            if qr_result.ok:
                self.verified_session = verified_session
                self.transition(DeviceState.CAPTURE_FACE, "qr verified; look at camera")
            else:
                self.transition(DeviceState.WAIT_QR, qr_result.message)
            return

        if self.state == DeviceState.CAPTURE_FACE:
            sleep_ms(DeviceConfig.FACE_CAPTURE_DELAY_MS)
            self.transition(DeviceState.VERIFY_FACE, "verifying face")
            return

        if self.state == DeviceState.VERIFY_FACE:
            frame = self.camera.capture()
            if not frame:
                self.transition(DeviceState.MARK_FAIL, "camera capture failed during face check")
                return
            face_result, student = self.api.verify_face(frame, self.verified_session.token)
            self.camera.release(frame)
            if face_result.ok:
                self.matched_student = student
                self.transition(
                    DeviceState.FACE_VERIFIED,
                    "face verified for {0}; use fingerprint device".format(student.student_code),
                )
            else:
                self.transition(DeviceState.MARK_FAIL, face_result.message)
            return

        if self.state == DeviceState.FACE_VERIFIED:
            if ticks_diff(monotonic_ms(), self.state_started_at) >= 5000:
                self._reset_verification_context()
                next_state, _ = self._ready_state_for_active_session()
                self.transition(next_state, "camera ready for next student")
            return

        if self.state == DeviceState.MARK_FAIL:
            sleep_ms(1200)
            self._reset_verification_context()
            next_state, _ = self._ready_state_for_active_session()
            self.transition(next_state, "ready for next camera attempt")
            return

        if self.state == DeviceState.ERROR_RECOVERY:
            if self.wifi.is_connected():
                next_state, message = self._ready_state_for_active_session()
                self.transition(next_state, message)
            else:
                sleep_ms(500)
