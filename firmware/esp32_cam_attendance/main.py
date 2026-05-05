try:
    from .api_client import ApiClient
    from .camera_service import CameraService
    from .config import DeviceConfig
    from .fingerprint_service import FingerprintService
    from .qr_service import QrService
    from .relay_service import RelayService
    from .runtime import StatusServer, WifiAdapter, log, sleep_ms
    from .state_machine import CameraStateMachine
    from .storage_service import StorageService
except ImportError:
    from api_client import ApiClient
    from camera_service import CameraService
    from config import DeviceConfig
    from fingerprint_service import FingerprintService
    from qr_service import QrService
    from relay_service import RelayService
    from runtime import StatusServer, WifiAdapter, log, sleep_ms
    from state_machine import CameraStateMachine
    from storage_service import StorageService


class CameraDeviceApp:
    def __init__(self):
        self.wifi = WifiAdapter()
        self.storage_service = StorageService()
        self.camera_service = CameraService()
        self.fingerprint_service = FingerprintService()
        self.relay_service = RelayService()
        self.api_client = ApiClient(wifi=self.wifi)
        self.qr_service = QrService(self.camera_service, self.api_client)
        self.state_machine = CameraStateMachine(
            self.camera_service,
            self.api_client,
            self.qr_service,
            self.storage_service,
            self.wifi,
            self.fingerprint_service,
            self.relay_service,
        )
        self.status_server = StatusServer(
            enabled=DeviceConfig.ENABLE_STATUS_WEB,
            port=DeviceConfig.STATUS_WEB_PORT,
            state_provider=self._status_snapshot,
            capture_provider=self.camera_service.capture,
        )

    def _status_snapshot(self):
        return {
            "state": self.state_machine.state_name(),
            "message": self.state_machine.last_message(),
            "ip_address": self.wifi.ip_address(),
            "last_error": self.storage_service.get_last_error(),
            "fingerprint_ready": self.fingerprint_service.sensor_ready(),
        }

    def connect_wifi(self):
        log("wifi", "connecting to {0}".format(DeviceConfig.WIFI_SSID))
        connected = self.wifi.connect(
            DeviceConfig.WIFI_SSID,
            DeviceConfig.WIFI_PASSWORD,
            DeviceConfig.WIFI_CONNECT_TIMEOUT_MS,
        )
        if connected:
            log("wifi", "connected, ip={0} rssi={1}".format(self.wifi.ip_address(), self.wifi.rssi()))
        else:
            log("wifi", "connection timeout")

    def setup(self):
        sleep_ms(1500)
        log("boot", "full attendance device starting (camera + fingerprint)")

        self.storage_service.begin()
        boot_count = self.storage_service.increment_boot_count()
        log(
            "boot",
            "count={0} last_state={1}".format(boot_count, self.storage_service.get_last_state()),
        )

        self.connect_wifi()
        self.camera_service.begin()
        self.fingerprint_service.begin()
        self.relay_service.begin()
        self.status_server.start()
        self.state_machine.begin()

    def loop_forever(self):
        while True:
            if not self.wifi.is_connected():
                self.connect_wifi()
            self.state_machine.tick()
            sleep_ms(50)


def main():
    app = CameraDeviceApp()
    app.setup()
    app.loop_forever()


if __name__ == "__main__":
    main()
