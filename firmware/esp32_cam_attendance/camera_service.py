try:
    from .config import DeviceConfig
    from .pins import Pins
    from .runtime import import_camera_module, log
except ImportError:
    from config import DeviceConfig
    from pins import Pins
    from runtime import import_camera_module, log

try:
    import _thread
    _camera_lock = _thread.allocate_lock()
except ImportError:
    _camera_lock = None


class CameraService:
    def __init__(self, capture_provider=None):
        self._camera = import_camera_module()
        self._capture_provider = capture_provider
        self._ready = False

    def begin(self):
        if self._capture_provider is not None:
            self._ready = True
            log("camera", "using injected capture provider")
            return True

        if self._camera is None:
            log("camera", "camera module unavailable; capture() will return None")
            return False

        try:
            frame_size = getattr(
                self._camera,
                "FRAME_{0}".format(DeviceConfig.FRAME_SIZE.upper()),
                None,
            )
            xclk_freq = getattr(self._camera, "XCLK_10MHz", 10000000)
            jpeg_format = getattr(self._camera, "JPEG", None)
            psram = getattr(self._camera, "PSRAM", None)
            init_kwargs = {
                "format": jpeg_format,
                "framesize": frame_size,
                "xclk_freq": xclk_freq,
                "d0": Pins.Y2_GPIO_NUM,
                "d1": Pins.Y3_GPIO_NUM,
                "d2": Pins.Y4_GPIO_NUM,
                "d3": Pins.Y5_GPIO_NUM,
                "d4": Pins.Y6_GPIO_NUM,
                "d5": Pins.Y7_GPIO_NUM,
                "d6": Pins.Y8_GPIO_NUM,
                "d7": Pins.Y9_GPIO_NUM,
                "xclk": Pins.XCLK_GPIO_NUM,
                "pclk": Pins.PCLK_GPIO_NUM,
                "vsync": Pins.VSYNC_GPIO_NUM,
                "href": Pins.HREF_GPIO_NUM,
                "siod": Pins.SIOD_GPIO_NUM,
                "sioc": Pins.SIOC_GPIO_NUM,
                "pwdn": Pins.PWDN_GPIO_NUM,
                "reset": Pins.RESET_GPIO_NUM if Pins.RESET_GPIO_NUM is not None else -1,
                "quality": DeviceConfig.JPEG_QUALITY,
            }
            if psram is not None:
                init_kwargs["fb_location"] = psram

            self._camera.init(
                0,
                **init_kwargs
            )
            self._ready = True
            log("camera", "ready")
            return True
        except Exception as exc:
            log("camera", "init failed: {0}".format(exc))
            return False

    def ready(self):
        return self._ready or self._camera is not None

    def capture(self):
        if _camera_lock is not None:
            if not _camera_lock.acquire(False):
                return None
        try:
            if self._capture_provider is not None:
                return self._capture_provider()
            if not self._ready:
                self.begin()
            if not self._ready or self._camera is None:
                log("camera", "capture failed")
                return None
            try:
                frame = self._camera.capture()
                if not frame:
                    log("camera", "capture failed")
                return frame
            except Exception as exc:
                log("camera", "capture failed: {0}".format(exc))
                return None
        finally:
            if _camera_lock is not None:
                _camera_lock.release()

    def release(self, frame):
        return None
