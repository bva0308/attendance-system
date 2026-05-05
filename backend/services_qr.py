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
    for candidate in _qr_decode_candidates(image):
        try:
            data, _, _ = detector.detectAndDecode(candidate)
        except cv2.error:
            continue
        if data:
            return data
    return None


def _qr_decode_candidates(image):
    yield image

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    yield cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    equalized = cv2.equalizeHist(gray)
    yield cv2.cvtColor(equalized, cv2.COLOR_GRAY2BGR)

    blurred = cv2.GaussianBlur(gray, (0, 0), 1.2)
    sharpened = cv2.addWeighted(gray, 1.8, blurred, -0.8, 0)
    yield cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)

    for scale in (2, 3):
        upscaled = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        yield upscaled

        up_gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
        yield cv2.cvtColor(up_gray, cv2.COLOR_GRAY2BGR)

        up_equalized = cv2.equalizeHist(up_gray)
        yield cv2.cvtColor(up_equalized, cv2.COLOR_GRAY2BGR)

        up_blurred = cv2.GaussianBlur(up_gray, (0, 0), 1.2)
        up_sharpened = cv2.addWeighted(up_gray, 1.8, up_blurred, -0.8, 0)
        yield cv2.cvtColor(up_sharpened, cv2.COLOR_GRAY2BGR)

        _, otsu = cv2.threshold(up_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        yield cv2.cvtColor(otsu, cv2.COLOR_GRAY2BGR)
