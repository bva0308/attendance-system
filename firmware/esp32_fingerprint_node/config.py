import json


def _load_settings(path="fingerprint_settings.json"):
    try:
        with open(path, "r") as handle:
            return json.load(handle) or {}
    except Exception:
        return {}


class DeviceConfig:
    WIFI_SSID = "dipesh regmi"
    WIFI_PASSWORD = "00000000"
    BACKEND_BASE_URL = "http://192.168.137.1:5000"
    DEVICE_ID = "esp32finger-lab-01"
    DEVICE_API_KEY = "demo-device-key"
    FIRMWARE_VERSION = "v1.0.0-fingerprint-node"

    WIFI_CONNECT_TIMEOUT_MS = 20000
    HEARTBEAT_INTERVAL_MS = 15000
    COMMAND_POLL_INTERVAL_MS = 2000
    PENDING_POLL_INTERVAL_MS = 1000
    FINGERPRINT_TIMEOUT_MS = 12000

    R307_UART_TX_PIN = 17
    R307_UART_RX_PIN = 16


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
