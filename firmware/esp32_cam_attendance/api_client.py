import json

try:
    from .config import DeviceConfig
    from .models import GenericResult, SessionInfo, StudentInfo
    from .runtime import HttpClient
except ImportError:
    from config import DeviceConfig
    from models import GenericResult, SessionInfo, StudentInfo
    from runtime import HttpClient


class ApiClient:
    def __init__(self, http_client=None, wifi=None):
        self.http = http_client or HttpClient()
        self.wifi = wifi

    def _endpoint_url(self, path):
        base_url = DeviceConfig.BACKEND_BASE_URL.rstrip("/")
        return base_url + path

    def _headers(self):
        return {
            "X-Device-Id": DeviceConfig.DEVICE_ID,
            "X-Device-Key": DeviceConfig.DEVICE_API_KEY,
        }

    def _parse_json_response(self, status_code, payload, fallback_message):
        if status_code <= 0:
            return None, GenericResult(False, "http request failed")
        try:
            parsed = json.loads(payload or "{}")
        except Exception:
            return None, GenericResult(False, fallback_message)
        return parsed, GenericResult.from_response(parsed)

    def post_heartbeat(self, state, wifi_rssi):
        payload = {
            "state": state,
            "wifi_rssi": wifi_rssi,
            "firmware_version": DeviceConfig.FIRMWARE_VERSION,
            "ip_address": self.wifi.ip_address() if self.wifi is not None else "0.0.0.0",
        }
        status_code, body = self.http.request(
            "POST",
            self._endpoint_url("/api/device/heartbeat"),
            headers=dict(self._headers(), **{"Content-Type": "application/json"}),
            json_body=payload,
        )
        parsed, result = self._parse_json_response(status_code, body, "invalid json response")
        if not parsed:
            return False, SessionInfo(), 0
        return result.ok, SessionInfo.from_dict(parsed.get("active_session")), int(parsed.get("pending_commands") or 0)

    def verify_qr(self, frame_bytes):
        status_code, body = self.http.request(
            "POST",
            self._endpoint_url("/api/device/verify-qr"),
            headers=dict(self._headers(), **{"Content-Type": "application/octet-stream"}),
            data=frame_bytes,
        )
        parsed, result = self._parse_json_response(status_code, body, "invalid qr response")
        if not result.ok or not parsed:
            return result, SessionInfo()
        return GenericResult(True, "qr verified"), SessionInfo.from_dict(parsed.get("session"))

    def verify_face(self, frame_bytes, session_token):
        status_code, body = self.http.request(
            "POST",
            self._endpoint_url("/api/device/verify-face"),
            headers=dict(
                self._headers(),
                **{
                    "Content-Type": "application/octet-stream",
                    "X-Session-Token": session_token,
                }
            ),
            data=frame_bytes,
        )
        parsed, result = self._parse_json_response(status_code, body, "invalid face response")
        if not result.ok or not parsed:
            return result, StudentInfo()
        return GenericResult(True, "face verified"), StudentInfo.from_dict(parsed.get("student"))

    def mark_attendance(self, session_token, student_id, by_qr, by_face, by_fingerprint):
        payload = {
            "session_token": session_token,
            "student_id": student_id,
            "verified_by_qr": by_qr,
            "verified_by_face": by_face,
            "verified_by_fingerprint": by_fingerprint,
        }
        status_code, body = self.http.request(
            "POST",
            self._endpoint_url("/api/device/mark-attendance"),
            headers=dict(self._headers(), **{"Content-Type": "application/json"}),
            json_body=payload,
        )
        parsed, result = self._parse_json_response(status_code, body, "invalid mark-attendance response")
        return result.ok, result.message

    def fingerprint_status(self, session_token, student_id):
        path = "/api/device/fingerprint-status?session_token={0}&student_id={1}".format(session_token, student_id)
        status_code, body = self.http.request(
            "GET",
            self._endpoint_url(path),
            headers=self._headers(),
        )
        parsed, result = self._parse_json_response(status_code, body, "invalid fingerprint status response")
        if not result.ok or not parsed:
            return "unknown", result.message
        return parsed.get("status", "unknown"), parsed.get("message", "")

    def log_verification_failure(self, session_token, student_id, status, note):
        payload = {
            "session_token": session_token,
            "student_id": student_id,
            "status": status,
            "note": note,
            "verified_by_qr": True,
            "verified_by_face": student_id is not None,
            "verified_by_fingerprint": False,
        }
        status_code, body = self.http.request(
            "POST",
            self._endpoint_url("/api/device/log-verification-failure"),
            headers=dict(self._headers(), **{"Content-Type": "application/json"}),
            json_body=payload,
        )
        parsed, result = self._parse_json_response(status_code, body, "invalid failure-log response")
        return result.ok
