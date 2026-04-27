from io import BytesIO

import qrcode

try:
    import cv2
    import numpy as np
    _cv2_available = True
except ImportError:
    _cv2_available = False


def generate_qr_png(payload: str) -> bytes:
    image = qrcode.make(payload)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def decode_qr_from_bytes(image_bytes: bytes) -> str | None:
    if not _cv2_available:
        return None
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        return None
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(image)
    return data or None
