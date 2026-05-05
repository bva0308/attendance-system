import json
import time

try:
    import network
except ImportError:
    network = None

try:
    import socket
except ImportError:
    socket = None


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
    else:
        time.sleep(duration_ms / 1000.0)


class WifiAdapter:
    def __init__(self):
        self._wlan = network.WLAN(network.STA_IF) if network is not None else None

    def connect(self, ssid, password, timeout_ms):
        if self._wlan is None:
            return True
        self._wlan.active(True)
        if self._wlan.isconnected():
            return True
        self._wlan.disconnect()
        sleep_ms(250)
        self._wlan.connect(ssid, password)
        started_at = monotonic_ms()
        while not self._wlan.isconnected() and ticks_diff(monotonic_ms(), started_at) < timeout_ms:
            sleep_ms(400)
        return self._wlan.isconnected()

    def is_connected(self):
        return True if self._wlan is None else self._wlan.isconnected()

    def ip_address(self):
        if self._wlan is None or not self._wlan.isconnected():
            return "0.0.0.0"
        return self._wlan.ifconfig()[0]

    def rssi(self):
        try:
            return self._wlan.status("rssi")
        except Exception:
            return -100


class HttpClient:
    def _parse_http_url(self, url):
        if not url.startswith("http://"):
            raise ValueError("only http:// URLs are supported")
        host_port, _, path = url[7:].partition("/")
        host, _, port_text = host_port.partition(":")
        return host, int(port_text or 80), "/" + path

    def request(self, method, url, headers=None, json_body=None):
        headers = headers or {}
        body = b""
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"

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
        except Exception as exc:
            log("http", "{0} {1} failed: {2}".format(method, url, exc))
            return 0, ""
        finally:
            try:
                conn.close()
            except Exception:
                pass

        raw = b"".join(chunks)
        header_bytes, _, body_bytes = raw.partition(b"\r\n\r\n")
        try:
            status_code = int(header_bytes.split(b"\r\n", 1)[0].split()[1])
        except Exception:
            status_code = 0
        try:
            return status_code, body_bytes.decode("utf-8")
        except Exception:
            return status_code, ""
