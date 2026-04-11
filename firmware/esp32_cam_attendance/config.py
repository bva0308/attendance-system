import json


def _load_settings(path="device_settings.json"):
    try:
        with open(path, "r") as handle:
            return json.load(handle) or {}
    except Exception:
        return {}


class DeviceConfig:
    WIFI_SSID = "LOKRAJ"
    WIFI_PASSWORD = "1808@7870"
    BACKEND_BASE_URL = "http://192.168.2.8:5000"
    DEVICE_ID = "esp32cam-lab-01"
    DEVICE_API_KEY = "demo-device-key"
    FIRMWARE_VERSION = "v1.0.0-python"

    WIFI_CONNECT_TIMEOUT_MS = 20000
    HEARTBEAT_INTERVAL_MS = 15000
    COMMAND_POLL_INTERVAL_MS = 5000
    QR_SCAN_INTERVAL_MS = 2000
    FACE_CAPTURE_DELAY_MS = 1000
    FINGERPRINT_TIMEOUT_MS = 10000
    STATE_TIMEOUT_MS = 15000
    RELAY_PULSE_MS = 2000

    JPEG_QUALITY = 12
    FRAME_SIZE = "VGA"

    RELAY_ACTIVE_HIGH = True
    ENABLE_STATUS_WEB = True
    ENABLE_EXTERNAL_STATUS_LED = False

    STATUS_WEB_PORT = 80
    STORAGE_PATH = "attendance_store.json"


_OVERRIDES = _load_settings()

if _OVERRIDES.get("wifi_ssid"):
    DeviceConfig.WIFI_SSID = _OVERRIDES["wifi_ssid"]
if _OVERRIDES.get("wifi_password"):
    DeviceConfig.WIFI_PASSWORD = _OVERRIDES["wifi_password"]
if _OVERRIDES.get("backend_base_url"):
    DeviceConfig.BACKEND_BASE_URL = str(_OVERRIDES["backend_base_url"]).rstrip("/")
if _OVERRIDES.get("device_id"):
    DeviceConfig.DEVICE_ID = _OVERRIDES["device_id"]
if _OVERRIDES.get("device_api_key"):
    DeviceConfig.DEVICE_API_KEY = _OVERRIDES["device_api_key"]
if _OVERRIDES.get("status_web_port"):
    DeviceConfig.STATUS_WEB_PORT = int(_OVERRIDES["status_web_port"])
