import json

from config import DeviceConfig
from runtime import HttpClient


class ApiClient:
    def __init__(self, wifi=None):
        self.http = HttpClient()
        self.wifi = wifi

    def _url(self, path):
        return DeviceConfig.BACKEND_BASE_URL.rstrip("/") + path

    def _headers(self):
        return {
            "X-Device-Id": DeviceConfig.DEVICE_ID,
            "X-Device-Key": DeviceConfig.DEVICE_API_KEY,
        }

    def _json(self, status, body):
        try:
            parsed = json.loads(body or "{}")
        except Exception:
            parsed = {}
        return status, parsed

    def heartbeat(self, state, rssi):
        payload = {
            "state": state,
            "wifi_rssi": rssi,
            "firmware_version": DeviceConfig.FIRMWARE_VERSION,
            "ip_address": self.wifi.ip_address() if self.wifi else "0.0.0.0",
        }
        status, body = self.http.request("POST", self._url("/api/device/heartbeat"), headers=self._headers(), json_body=payload)
        return self._json(status, body)

    def next_command(self):
        status, body = self.http.request("GET", self._url("/api/device/commands/next"), headers=self._headers())
        return self._json(status, body)

    def complete_command(self, command_id, status_text, template_id=0, message=""):
        payload = {"status": status_text, "template_id": template_id, "message": message}
        status, body = self.http.request(
            "POST",
            self._url("/api/device/commands/{0}/complete".format(command_id)),
            headers=self._headers(),
            json_body=payload,
        )
        return self._json(status, body)

    def pending_fingerprint(self):
        status, body = self.http.request("GET", self._url("/api/device/pending-fingerprint"), headers=self._headers())
        return self._json(status, body)

    def complete_fingerprint(self, pending_id, template_id):
        payload = {"pending_id": pending_id, "template_id": template_id}
        status, body = self.http.request(
            "POST",
            self._url("/api/device/complete-fingerprint"),
            headers=self._headers(),
            json_body=payload,
        )
        return self._json(status, body)
