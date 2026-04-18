try:
    from .models import GenericResult, SessionInfo
except ImportError:
    from models import GenericResult, SessionInfo


class QrService:
    def __init__(self, camera_service, api_client):
        self.camera = camera_service
        self.api = api_client

    def verify_session_qr(self):
        frame = self.camera.capture()
        if not frame:
            return GenericResult(False, "camera capture failed during qr scan"), SessionInfo()
        result, session = self.api.verify_qr(frame)
        self.camera.release(frame)
        return result, session
