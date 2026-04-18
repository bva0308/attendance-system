# API Specification

All device APIs require:

- `X-Device-Id`
- `X-Device-Key`

## `POST /api/device/heartbeat`

Request JSON:

```json
{
  "state": "WAIT_QR",
  "wifi_rssi": -61,
  "firmware_version": "v1.0.0",
  "ip_address": "192.168.1.77"
}
```

Response JSON:

```json
{
  "ok": true,
  "active_session": {
    "id": 1,
    "title": "Embedded Systems Demo",
    "class_name": "ECE-8",
    "session_token": "demo-session-token",
    "starts_at": "2026-04-12T12:00:00",
    "ends_at": "2026-04-12T16:00:00",
    "allow_duplicates": false
  },
  "pending_commands": 0
}
```

## `GET /api/device/commands/next`

Returns queued command or `null`.

## `POST /api/device/commands/<id>/complete`

Request JSON:

```json
{
  "status": "completed",
  "template_id": 3,
  "message": "fingerprint enrolled"
}
```

## `POST /api/device/verify-qr`

Request body:

- Raw JPEG bytes
- `Content-Type: application/octet-stream`

Response:

- `200 OK` with session metadata if valid
- `400` if QR missing, invalid, inactive, or outside session time window

## `POST /api/device/verify-face`

Headers:

- `X-Session-Token`

Body:

- Raw JPEG bytes

Response:

```json
{
  "ok": true,
  "student": {
    "id": 1,
    "student_code": "STU001",
    "full_name": "Demo Student",
    "class_name": "ECE-8",
    "fingerprint_template_id": 3
  },
  "distance": 0.41
}
```

## `POST /api/device/mark-attendance`

Request JSON:

```json
{
  "session_token": "demo-session-token",
  "student_id": 1,
  "verified_by_qr": true,
  "verified_by_face": true,
  "verified_by_fingerprint": true,
  "note": "Marked from ESP32-CAM prototype"
}
```

Possible responses:

- `200 OK` on success
- `409` when duplicate attendance is rejected
- `400` when class mismatch or bad data is detected
