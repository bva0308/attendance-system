# Architecture

## Practical Split

This prototype uses a split architecture because the original ESP32-CAM is constrained in RAM, CPU, and stable peripheral availability.

### ESP32-CAM responsibilities

- Connect to Wi-Fi
- Capture JPEG frames from OV2640
- Poll backend for active session and queued fingerprint enrollment commands
- Drive the verification state machine
- Trigger local fingerprint match using R307
- Trigger relay output on success
- Publish heartbeat and send attendance result to backend

### Backend responsibilities

- Admin authentication
- Student, session, attendance, and device storage
- QR payload generation and QR decode from uploaded device frame
- Face profile enrollment and face matching
- Attendance duplication rules
- Device command queue for fingerprint enrollment
- HTML dashboard and CSV export

## Why QR and Face Are Backend-Side

For this board, the stable engineering choice is to keep only capture and transport on-device.

- Backend QR decoding is more dependable than trying to run QR decode plus camera plus Wi-Fi plus fingerprint in one MCU loop.
- Backend face verification is much more realistic than claiming stable edge face recognition on original ESP32-CAM hardware.
- This makes the prototype honest and maintainable while still demonstrating full multi-factor verification.

## State Machine

- `IDLE`
- `WAIT_QR`
- `VERIFY_QR`
- `CAPTURE_FACE`
- `VERIFY_FACE`
- `WAIT_FINGER`
- `VERIFY_FINGER`
- `MARK_SUCCESS`
- `MARK_FAIL`
- `ERROR_RECOVERY`

## Data Flow

1. Device heartbeat asks backend for active session metadata.
2. Device scans QR by sending captured JPEG to `/api/device/verify-qr`.
3. Device captures face and sends JPEG to `/api/device/verify-face`.
4. Backend returns matched student and expected fingerprint template ID.
5. Device verifies the matched fingerprint locally on the R307.
6. Device calls `/api/device/mark-attendance`.
7. Relay pulses after successful backend response.
