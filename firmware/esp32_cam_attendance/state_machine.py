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
    WAIT_FINGER = "WAIT_FINGER"
    VERIFY_FINGER = "VERIFY_FINGER"
    MARK_SUCCESS = "MARK_SUCCESS"
    MARK_FAIL = "MARK_FAIL"
    ERROR_RECOVERY = "ERROR_RECOVERY"


class AttendanceStateMachine:
    def __init__(self, camera_service, fingerprint_service, api_client, qr_service, relay_service, storage_service, wifi):
        self.camera = camera_service
        self.fingerprint = fingerprint_service
        self.api = api_client
        self.qr = qr_service
        self.relay = relay_service
        self.storage = storage_service
        self.wifi = wifi

        self.state = DeviceState.IDLE
        self.message = "boot"
        self.active_session = SessionInfo()
        self.verified_session = SessionInfo()
        self.matched_student = StudentInfo()

        self.state_started_at = 0
        self.last_heartbeat_at = 0
        self.last_command_poll_at = 0
        self.last_qr_attempt_at = 0
        self.pending_commands = 0

    def begin(self):
        self.transition(DeviceState.IDLE, "waiting for active session")

    def state_name(self):
        return self.state

    def last_message(self):
        return self.message

    def _reset_verification_context(self):
        self.verified_session = SessionInfo()
        self.matched_student = StudentInfo()

    def _current_session(self):
        return self.verified_session if self.verified_session.valid else self.active_session

    def _ready_state_for_active_session(self):
        if not self.active_session.valid:
            return DeviceState.IDLE, "no active session"
        if self.camera.ready():
            return DeviceState.WAIT_QR, "active session ready; present qr"
        return DeviceState.WAIT_FINGER, "active session ready; place registered finger"

    def _is_verification_state(self):
        return self.state in (
            DeviceState.CAPTURE_FACE,
            DeviceState.VERIFY_FACE,
            DeviceState.WAIT_FINGER,
            DeviceState.VERIFY_FINGER,
            DeviceState.MARK_SUCCESS,
            DeviceState.MARK_FAIL,
        )

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
        ok, heartbeat_session, pending_commands = self.api.post_heartbeat(self.state_name(), self.wifi.rssi())
        if ok:
            self.active_session = heartbeat_session
            self.pending_commands = pending_commands
        else:
            self.active_session = SessionInfo()
            self.pending_commands = 0

    def check_commands(self):
        if ticks_diff(monotonic_ms(), self.last_command_poll_at) < DeviceConfig.COMMAND_POLL_INTERVAL_MS:
            return False
        self.last_command_poll_at = monotonic_ms()
        command = self.api.fetch_next_command()
        if not command.available or command.type != "enroll_fingerprint":
            return False

        log("command", "enrolling fingerprint for {0}".format(command.student_code))
        ok, template_id, enroll_message = self.fingerprint.enroll_next_template()
        self.api.complete_command(command.id, "completed" if ok else "failed", template_id, enroll_message)
        self.pending_commands = 0
        self.transition(DeviceState.IDLE, "command processed")
        return True

    def tick(self):
        self.do_heartbeat()
        handled_command = self.check_commands()
        if handled_command:
            return

        if not self.wifi.is_connected() and self.state != DeviceState.ERROR_RECOVERY:
            self._reset_verification_context()
            self.transition(DeviceState.ERROR_RECOVERY, "wifi disconnected")
            return

        if self.pending_commands > 0:
            if self.state != DeviceState.IDLE or self.message != "waiting for queued device command":
                self._reset_verification_context()
                self.transition(DeviceState.IDLE, "waiting for queued device command")
            return

        if (
            self.state not in (DeviceState.IDLE, DeviceState.WAIT_QR, DeviceState.ERROR_RECOVERY)
            and ticks_diff(monotonic_ms(), self.state_started_at) >= DeviceConfig.STATE_TIMEOUT_MS
        ):
            self.transition(DeviceState.MARK_FAIL, "state timeout")
            return

        if self._is_verification_state() and self.verified_session.valid:
            if not self.active_session.valid or self.active_session.token != self.verified_session.token:
                self._reset_verification_context()
                self.transition(
                    DeviceState.WAIT_QR if self.active_session.valid else DeviceState.IDLE,
                    "active session changed",
                )
                return

        if self.state == DeviceState.IDLE:
            if self.active_session.valid:
                next_state, message = self._ready_state_for_active_session()
                self.transition(next_state, message)
            return

        if self.state == DeviceState.WAIT_QR:
            if not self.active_session.valid:
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
                self.transition(DeviceState.WAIT_FINGER, "camera unavailable; using fingerprint attendance")
                return
            face_result, student = self.api.verify_face(frame, self.verified_session.token)
            self.camera.release(frame)
            if face_result.ok:
                self.matched_student = student
                self.transition(DeviceState.WAIT_FINGER, "place registered finger on sensor")
            else:
                self.transition(DeviceState.MARK_FAIL, face_result.message)
            return

        if self.state == DeviceState.WAIT_FINGER:
            self.transition(
                DeviceState.VERIFY_FINGER,
                "verifying fingerprint" if self.matched_student.valid else "identifying fingerprint",
            )
            return

        if self.state == DeviceState.VERIFY_FINGER:
            current_session = self._current_session()
            if self.matched_student.valid:
                ok, finger_message = self.fingerprint.verify_template(
                    self.matched_student.fingerprint_template_id,
                    DeviceConfig.FINGERPRINT_TIMEOUT_MS,
                )
                if ok:
                    self.transition(DeviceState.MARK_SUCCESS, "all factors verified")
                else:
                    if current_session.valid and self.matched_student.valid:
                        self.api.log_verification_failure(current_session, self.matched_student, finger_message)
                    self.transition(DeviceState.MARK_FAIL, finger_message)
            else:
                ok, template_id, finger_message = self.fingerprint.identify_template(DeviceConfig.FINGERPRINT_TIMEOUT_MS)
                if not ok:
                    if current_session.valid:
                        self.api.log_verification_failure(current_session, None, finger_message)
                    self.transition(DeviceState.MARK_FAIL, finger_message)
                    return
                resolve_result, student = self.api.resolve_fingerprint_student(current_session.token, template_id)
                if resolve_result.ok and student.valid:
                    self.matched_student = student
                    self.transition(DeviceState.MARK_SUCCESS, "fingerprint identified")
                else:
                    if current_session.valid:
                        self.api.log_verification_failure(current_session, None, resolve_result.message)
                    self.transition(DeviceState.MARK_FAIL, resolve_result.message)
            return

        if self.state == DeviceState.MARK_SUCCESS:
            current_session = self._current_session()
            mark_result = self.api.mark_attendance(current_session, self.matched_student)
            if mark_result.ok:
                self.relay.pulse(DeviceConfig.RELAY_PULSE_MS)
                self.active_session = current_session
                self._reset_verification_context()
                next_state, _ = self._ready_state_for_active_session()
                self.transition(next_state, "attendance marked successfully")
            else:
                if current_session.valid and self.matched_student.valid:
                    self.api.log_verification_failure(
                        current_session,
                        self.matched_student,
                        mark_result.message,
                        verified_by_fingerprint=True,
                    )
                self.transition(DeviceState.MARK_FAIL, mark_result.message)
            return

        if self.state == DeviceState.MARK_FAIL:
            sleep_ms(1200)
            self._reset_verification_context()
            next_state, _ = self._ready_state_for_active_session()
            self.transition(next_state, "ready for next attempt")
            return

        if self.state == DeviceState.ERROR_RECOVERY:
            if self.wifi.is_connected():
                self.transition(
                    DeviceState.WAIT_QR if self.active_session.valid else DeviceState.IDLE,
                    "recovered from error",
                )
            else:
                sleep_ms(500)
