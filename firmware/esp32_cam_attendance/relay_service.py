try:
    from .config import DeviceConfig
    from .pins import Pins
    from .runtime import PinWriter, sleep_ms
except ImportError:
    from config import DeviceConfig
    from pins import Pins
    from runtime import PinWriter, sleep_ms


class RelayService:
    def __init__(self, pin_number=Pins.RELAY_PIN):
        self._pin = PinWriter(pin_number)

    def begin(self):
        self._pin.begin_output()
        self._pin.write(0 if DeviceConfig.RELAY_ACTIVE_HIGH else 1)

    def pulse(self, duration_ms):
        self._pin.write(1 if DeviceConfig.RELAY_ACTIVE_HIGH else 0)
        sleep_ms(duration_ms)
        self._pin.write(0 if DeviceConfig.RELAY_ACTIVE_HIGH else 1)
