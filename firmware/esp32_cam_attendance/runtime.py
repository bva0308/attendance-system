import json
import os
import time


try:
    import _thread
except ImportError:
    _thread = None

try:
    import network
except ImportError:
    network = None

try:
    import urequests as requests_backend
except ImportError:
    try:
        import requests as requests_backend
    except ImportError:
        requests_backend = None

try:
    import machine
except ImportError:
    machine = None

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    BaseHTTPRequestHandler = None
    HTTPServer = None


def log(tag, message):
    print("[{0}] {1}".format(tag, message))


def monotonic_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.monotonic() * 1000)


def ticks_diff(current, previous):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(current, previous)
    return current - previous


def sleep_ms(duration_ms):
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(int(duration_ms))
        return
    time.sleep(duration_ms / 1000.0)


class WifiAdapter:
    def __init__(self):
        self._mock_connected = True
        self._mock_ip = "127.0.0.1"
        self._mock_rssi = -45
        self._wlan = None
        if network is not None:
            self._wlan = network.WLAN(network.STA_IF)

    def connect(self, ssid, password, timeout_ms):
        if self._wlan is None:
            log("wifi", "network module unavailable; using connected mock")
            self._mock_connected = True
            return True

        self._wlan.active(True)
        if self._wlan.isconnected():
            return True

        self._wlan.connect(ssid, password)
        started_at = monotonic_ms()
        while not self._wlan.isconnected() and ticks_diff(monotonic_ms(), started_at) < timeout_ms:
            sleep_ms(400)
        return self._wlan.isconnected()

    def is_connected(self):
        if self._wlan is None:
            return self._mock_connected
        return self._wlan.isconnected()

    def ip_address(self):
        if self._wlan is None:
            return self._mock_ip
        if not self._wlan.isconnected():
            return "0.0.0.0"
        return self._wlan.ifconfig()[0]

    def rssi(self):
        if self._wlan is None:
            return self._mock_rssi
        try:
            return self._wlan.status("rssi")
        except Exception:
            return -100


class HttpClient:
    def request(self, method, url, headers=None, data=None, json_body=None):
        headers = headers or {}
        if requests_backend is None:
            log("http", "no HTTP client backend is available")
            return 0, ""

        try:
            if requests_backend.__name__ == "urequests":
                response = requests_backend.request(method, url, data=data, json=json_body, headers=headers)
                try:
                    return response.status_code, response.text
                finally:
                    response.close()

            response = requests_backend.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json_body,
                timeout=10,
            )
            return response.status_code, response.text
        except Exception as exc:
            log("http", "{0} {1} failed: {2}".format(method, url, exc))
            return 0, ""


class JsonStore:
    def __init__(self, path):
        self.path = path
        self.data = {}

    def load(self):
        try:
            with open(self.path, "r") as handle:
                self.data = json.load(handle)
        except OSError:
            self.data = {}
        except Exception:
            self.data = {}

    def save(self):
        with open(self.path, "w") as handle:
            json.dump(self.data, handle)


class PinWriter:
    def __init__(self, pin_number):
        self.pin_number = pin_number
        self._pin = None
        self._value = 0

    def begin_output(self):
        if machine is None:
            return
        self._pin = machine.Pin(self.pin_number, machine.Pin.OUT)

    def write(self, value):
        self._value = 1 if value else 0
        if self._pin is not None:
            self._pin.value(self._value)

    @property
    def value(self):
        return self._value


class StatusServer:
    def __init__(self, enabled, port, state_provider):
        self.enabled = enabled and HTTPServer is not None and BaseHTTPRequestHandler is not None and _thread is not None
        self.port = port
        self.state_provider = state_provider
        self._started = False

    def start(self):
        if not self.enabled or self._started:
            return

        provider = self.state_provider

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                state = provider()
                html = (
                    "<html><body><h1>ESP32-CAM Attendance Device</h1>"
                    "<p>State: {state}</p>"
                    "<p>Message: {message}</p>"
                    "<p>IP: {ip_address}</p>"
                    "<p>Last error: {last_error}</p>"
                    "</body></html>"
                ).format(
                    state=state.get("state", "UNKNOWN"),
                    message=state.get("message", ""),
                    ip_address=state.get("ip_address", "0.0.0.0"),
                    last_error=state.get("last_error", ""),
                )
                payload = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, fmt, *args):
                return

        def serve():
            server = HTTPServer(("", self.port), Handler)
            log("web", "debug status page enabled on port {0}".format(self.port))
            server.serve_forever()

        _thread.start_new_thread(serve, ())
        self._started = True


def import_camera_module():
    try:
        import camera

        return camera
    except ImportError:
        return None
