try:
    from .config import DeviceConfig
    from .runtime import JsonStore
except ImportError:
    from config import DeviceConfig
    from runtime import JsonStore


class StorageService:
    def __init__(self, path=None):
        self._store = JsonStore(path or DeviceConfig.STORAGE_PATH)

    def begin(self):
        self._store.load()

    def increment_boot_count(self):
        value = int(self._store.data.get("boot_count", 0)) + 1
        self._store.data["boot_count"] = value
        self._store.save()
        return value

    def save_last_state(self, state):
        self._store.data["last_state"] = state
        self._store.save()

    def get_last_state(self):
        return self._store.data.get("last_state", "unknown")

    def save_last_error(self, message):
        self._store.data["last_error"] = message
        self._store.save()

    def get_last_error(self):
        return self._store.data.get("last_error", "")
