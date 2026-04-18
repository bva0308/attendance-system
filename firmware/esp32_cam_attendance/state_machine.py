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

    def begin(self):
        self.transition(DeviceState.IDLE, "waiting for active session")

    def state_name(self):
        return self.state

    def last_message(self):
        return self.message

    def transition(self, next_state, next_message):
        previous_state = self.state
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
        ok, heartbeat_session = self.api.post_heartbeat(self.state_name(), self.wifi.rssi())
        if ok:
            self.active_session = heartbeat_session

    def check_commands(self):
        if ticks_diff(monotonic_ms(), self.last_command_poll_at) < DeviceConfig.COMMAND_POLL_INTERVAL_MS:
            return
        self.last_command_poll_at = monotonic_ms()
        command = self.api.fetch_next_command()
        if not command.available or command.type != "enroll_fingerprint":
            return

        log("command", "enrolling fingerprint for {0}".format(command.student_code))
        ok, template_id, enroll_message = self.fingerprint.enroll_next_template()
        self.api.complete_command(command.id, "completed" if ok else "failed", template_id, enroll_message)

    def tick(self):
        self.do_heartbeat()
        self.check_commands()

        if not self.wifi.is_connected():
            self.transition(DeviceState.ERROR_RECOVERY, "wifi disconnected")

        if self.state == DeviceState.IDLE:
            if self.active_session.valid:
                self.transition(DeviceState.WAIT_QR, "active session ready; present qr")
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
                self.transition(DeviceState.MARK_FAIL, "face capture failed")
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
            self.transition(DeviceState.VERIFY_FINGER, "verifying fingerprint")
            return

        if self.state == DeviceState.VERIFY_FINGER:
            ok, finger_message = self.fingerprint.verify_template(
                self.matched_student.fingerprint_template_id,
                DeviceConfig.FINGERPRINT_TIMEOUT_MS,
            )
            if ok:
                self.transition(DeviceState.MARK_SUCCESS, "all factors verified")
            else:
                self.transition(DeviceState.MARK_FAIL, finger_message)
            return

        if self.state == DeviceState.MARK_SUCCESS:
            mark_result = self.api.mark_attendance(self.verified_session, self.matched_student)
            if mark_result.ok:
                self.relay.pulse(DeviceConfig.RELAY_PULSE_MS)
                self.active_session = self.verified_session
                self.verified_session = SessionInfo()
                self.matched_student = StudentInfo()
                self.transition(DeviceState.WAIT_QR, "attendance marked successfully")
            else:
                self.transition(DeviceState.MARK_FAIL, mark_result.message)
            return

        if self.state == DeviceState.MARK_FAIL:
            sleep_ms(1200)
            self.verified_session = SessionInfo()
            self.matched_student = StudentInfo()
            self.transition(
                DeviceState.WAIT_QR if self.active_session.valid else DeviceState.IDLE,
                "ready for next attempt",
            )
            return

        if self.state == DeviceState.ERROR_RECOVERY:
            if self.wifi.is_connected():
                self.transition(
                    DeviceState.WAIT_QR if self.active_session.valid else DeviceState.IDLE,
                    "recovered from error",
                )
            else:
                sleep_ms(500)
