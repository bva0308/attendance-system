from api_client import ApiClient
from config import DeviceConfig
from fingerprint_service import FingerprintService
from runtime import WifiAdapter, log, monotonic_ms, sleep_ms, ticks_diff


class FingerprintNode:
    def __init__(self):
        self.wifi = WifiAdapter()
        self.api = ApiClient(wifi=self.wifi)
        self.finger = FingerprintService()
        self.state = "BOOT"
        self.last_heartbeat_at = 0
        self.last_command_poll_at = 0
        self.last_pending_poll_at = 0

    def set_state(self, state, message):
        self.state = state
        log("state", "{0}: {1}".format(state, message))

    def connect_wifi(self):
        self.set_state("WIFI_CONNECTING", "connecting wifi")
        if self.wifi.connect(DeviceConfig.WIFI_SSID, DeviceConfig.WIFI_PASSWORD, DeviceConfig.WIFI_CONNECT_TIMEOUT_MS):
            self.set_state("IDLE", "wifi connected ip={0}".format(self.wifi.ip_address()))
            return True
        self.set_state("ERROR_RECOVERY", "wifi connection timeout")
        return False

    def heartbeat(self):
        if ticks_diff(monotonic_ms(), self.last_heartbeat_at) < DeviceConfig.HEARTBEAT_INTERVAL_MS:
            return
        self.last_heartbeat_at = monotonic_ms()
        self.api.heartbeat(self.state, self.wifi.rssi())

    def handle_enroll_command(self, command):
        command_id = int(command.get("id") or 0)
        payload = command.get("payload") or {}
        self.set_state("ENROLL_FINGER", "enrolling {0}".format(payload.get("student_code", "student")))
        ok, template_id, message = self.finger.enroll_next_template()
        if ok:
            self.api.complete_command(command_id, "completed", template_id=template_id, message=message)
            self.set_state("IDLE", "enrolled template {0}".format(template_id))
        else:
            self.api.complete_command(command_id, "failed", message=message)
            self.set_state("IDLE", message)

    def poll_commands(self):
        if ticks_diff(monotonic_ms(), self.last_command_poll_at) < DeviceConfig.COMMAND_POLL_INTERVAL_MS:
            return
        self.last_command_poll_at = monotonic_ms()
        status, body = self.api.next_command()
        if status != 200 or not body.get("ok"):
            return
        command = body.get("command")
        if not command:
            return
        if command.get("type") == "enroll_fingerprint":
            self.handle_enroll_command(command)

    def poll_pending_fingerprint(self):
        if ticks_diff(monotonic_ms(), self.last_pending_poll_at) < DeviceConfig.PENDING_POLL_INTERVAL_MS:
            return
        self.last_pending_poll_at = monotonic_ms()
        status, body = self.api.pending_fingerprint()
        if status != 200 or not body.get("ok"):
            return
        pending = body.get("pending")
        if not pending:
            self.set_state("IDLE", "waiting for face-verified student")
            return

        student_name = pending.get("student_name") or pending.get("student_code") or "student"
        expected_template = int(pending.get("fingerprint_template_id") or 0)
        self.set_state("WAIT_FINGER", "place finger for {0}".format(student_name))
        ok, matched_template, message = self.finger.verify_expected_template(
            expected_template,
            DeviceConfig.FINGERPRINT_TIMEOUT_MS,
        )
        if ok:
            status, response = self.api.complete_fingerprint(int(pending.get("id")), matched_template)
            if status == 200 and response.get("ok"):
                self.set_state("SUCCESS", "attendance marked")
                sleep_ms(1500)
            else:
                self.set_state("WAIT_FINGER", response.get("error") or "backend rejected fingerprint")
        else:
            self.set_state("WAIT_FINGER", message)

    def setup(self):
        log("boot", "ESP32 fingerprint node starting")
        self.connect_wifi()
        self.finger.begin()

    def loop_forever(self):
        while True:
            if not self.wifi.is_connected():
                self.connect_wifi()
            self.heartbeat()
            self.poll_commands()
            self.poll_pending_fingerprint()
            sleep_ms(100)


def main():
    node = FingerprintNode()
    node.setup()
    node.loop_forever()


if __name__ == "__main__":
    main()
