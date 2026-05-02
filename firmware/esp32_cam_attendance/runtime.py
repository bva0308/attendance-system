import json
import os
import time


try:
    import socket
except ImportError:
    socket = None

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
    def _parse_http_url(self, url):
        if not url.startswith("http://"):
            raise ValueError("only http:// URLs are supported")
        without_scheme = url[7:]
        host_port, _, path = without_scheme.partition("/")
        path = "/" + path
        host, _, port_text = host_port.partition(":")
        return host, int(port_text or 80), path

    def _socket_request(self, method, url, headers=None, data=None, json_body=None):
        if socket is None:
            log("http", "no socket backend is available")
            return 0, ""

        headers = headers or {}
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
        elif data is not None:
            body = data
        else:
            body = b""
        if isinstance(body, str):
            body = body.encode("utf-8")

        host, port, path = self._parse_http_url(url)
        address = socket.getaddrinfo(host, port)[0][-1]
        conn = socket.socket()
        try:
            conn.connect(address)
            request_headers = [
                "{0} {1} HTTP/1.0".format(method, path),
                "Host: {0}".format(host),
                "Connection: close",
                "Content-Length: {0}".format(len(body)),
            ]
            for key, value in headers.items():
                request_headers.append("{0}: {1}".format(key, value))
            conn.send(("\r\n".join(request_headers) + "\r\n\r\n").encode("utf-8"))
            if body:
                conn.send(body)

            chunks = []
            while True:
                chunk = conn.recv(1024)
                if not chunk:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks)
        finally:
            conn.close()

        header_bytes, _, body_bytes = raw.partition(b"\r\n\r\n")
        status_line = header_bytes.split(b"\r\n", 1)[0]
        try:
            status_code = int(status_line.split()[1])
        except Exception:
            status_code = 0
        try:
            response_text = body_bytes.decode("utf-8")
        except Exception:
            response_text = ""
        return status_code, response_text

    def request(self, method, url, headers=None, data=None, json_body=None):
        headers = headers or {}
        if requests_backend is None:
            try:
                return self._socket_request(method, url, headers=headers, data=data, json_body=json_body)
            except Exception as exc:
                log("http", "{0} {1} failed: {2}".format(method, url, exc))
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
        except Exception:
            self.data = {}

    def save(self):
        try:
            with open(self.path, "w") as handle:
                json.dump(self.data, handle)
        except Exception as exc:
            log("store", "save skipped: {0}".format(exc))


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
    def __init__(self, enabled, port, state_provider, capture_provider=None):
        has_desktop_server = HTTPServer is not None and BaseHTTPRequestHandler is not None
        has_micro_server = socket is not None
        self.enabled = enabled and _thread is not None and (has_desktop_server or has_micro_server)
        self.port = port
        self.state_provider = state_provider
        self.capture_provider = capture_provider
        self._started = False

    def start(self):
        if not self.enabled or self._started:
            return
        if HTTPServer is None or BaseHTTPRequestHandler is None:
            self._start_micro_server()
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

    def _http_response(self, client, status, content_type, payload):
        header = (
            "HTTP/1.0 {0}\r\n"
            "Content-Type: {1}\r\n"
            "Cache-Control: no-store\r\n"
            "Content-Length: {2}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).format(status, content_type, len(payload))
        client.send(header.encode("utf-8"))
        client.send(payload)

    def _preview_html(self, state):
        return (
            "<!doctype html><html><head>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>ESP32-CAM Preview</title>"
            "<style>body{font-family:system-ui;margin:20px;background:#111;color:#fff}"
            "img{max-width:100%;height:auto;border:1px solid #444}"
            ".meta{color:#bbb;margin-bottom:12px}</style>"
            "</head><body><h1>ESP32-CAM Preview</h1>"
            "<p class='meta'>State: " + str(state.get("state", "UNKNOWN")) + "<br>Message: " + str(state.get("message", "")) + "</p>"
            "<img id='cam' src='/capture.jpg?0' alt='ESP32 camera preview'>"
            "<script>setInterval(function(){document.getElementById('cam').src='/capture.jpg?'+Date.now()},1000)</script>"
            "</body></html>"
        ).encode("utf-8")

    def _handle_micro_request(self, client):
        try:
            request = client.recv(512) or b""
            first_line = request.split(b"\r\n", 1)[0]
            parts = first_line.split()
            path = parts[1].decode("utf-8") if len(parts) > 1 else "/"
            path = path.split("?", 1)[0]

            if path == "/capture.jpg":
                frame = self.capture_provider() if self.capture_provider is not None else None
                if frame:
                    self._http_response(client, "200 OK", "image/jpeg", frame)
                else:
                    self._http_response(client, "503 Service Unavailable", "text/plain", b"camera capture failed")
                return

            state = self.state_provider()
            if path == "/preview":
                self._http_response(client, "200 OK", "text/html; charset=utf-8", self._preview_html(state))
                return

            html = (
                "<html><body><h1>ESP32-CAM Attendance Device</h1>"
                "<p>State: {state}</p>"
                "<p>Message: {message}</p>"
                "<p>IP: {ip_address}</p>"
                "<p>Last error: {last_error}</p>"
                "<p><a href='/preview'>Camera preview</a></p>"
                "</body></html>"
            ).format(
                state=state.get("state", "UNKNOWN"),
                message=state.get("message", ""),
                ip_address=state.get("ip_address", "0.0.0.0"),
                last_error=state.get("last_error", ""),
            ).encode("utf-8")
            self._http_response(client, "200 OK", "text/html; charset=utf-8", html)
        except Exception as exc:
            log("web", "request failed: {0}".format(exc))
        finally:
            try:
                client.close()
            except Exception:
                pass

    def _start_micro_server(self):
        def serve():
            address = socket.getaddrinfo("0.0.0.0", self.port)[0][-1]
            server = socket.socket()
            try:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except Exception:
                pass
            server.bind(address)
            server.listen(2)
            log("web", "preview/status server enabled on port {0}".format(self.port))
            while True:
                client, _ = server.accept()
                self._handle_micro_request(client)

        _thread.start_new_thread(serve, ())
        self._started = True


def import_camera_module():
    try:
        import camera

        return camera
    except ImportError:
        return None
