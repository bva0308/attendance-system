import json


def _load_settings(path="device_settings.json"):
    try:
        with open(path, "r") as handle:
            return json.load(handle) or {}
    except Exception:
        return {}


class DeviceConfig:
    WIFI_SSID = "dipesh regmi"
    WIFI_PASSWORD = "00000000"
    BACKEND_BASE_URL = "http://192.168.137.1:5000"
    DEVICE_ID = "esp32cam-lab-01"
    DEVICE_API_KEY = "demo-device-key"
    FIRMWARE_VERSION = "v1.2.0-full"

    WIFI_CONNECT_TIMEOUT_MS = 20000
    HEARTBEAT_INTERVAL_MS = 15000
    QR_SCAN_INTERVAL_MS = 2000
    FACE_SETTLE_DELAY_MS = 3000
    FACE_CAPTURE_DELAY_MS = 1500
    STATE_TIMEOUT_MS = 30000
    FINGERPRINT_SETTLE_DELAY_MS = 2000
    FINGERPRINT_TIMEOUT_MS = 10000

    JPEG_QUALITY = 12
    FRAME_SIZE = "VGA"

    RELAY_ACTIVE_HIGH = True
    RELAY_PULSE_MS = 2000
    USE_EXTERNAL_FINGERPRINT_NODE = True

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
