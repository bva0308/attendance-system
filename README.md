# IoT-Based Secure Attendance Verification System Using Multi-Factor Identity Methods

This repository is a realistic student prototype for an attendance verification system built around your actual hardware:

- ESP32-CAM AI Thinker with OV2640
- R307 UART fingerprint sensor
- 5V single-channel relay module
- 18650 cell + TP4056 charging module

The prototype is intentionally split so the ESP32-CAM only does what it can do reliably:

- ESP32-CAM handles Wi-Fi, camera capture, workflow state machine, fingerprint enrollment/matching through R307, relay output, and backend communication.
- Backend handles QR decoding, face verification, admin login, attendance storage, sessions, reports, and dashboard pages.
- The firmware directory in this repo is a Python port that mirrors the embedded workflow for development and review. The earlier Arduino/C++ sketch layout shown in older notes is no longer the source of truth here.

## Feasibility Summary

This is a practical prototype, not a fake full edge-AI system.

- Face verification is done on the backend because robust face recognition on original ESP32-CAM is not dependable enough for a final-year prototype.
- QR decoding is also handled on the backend from camera frames. This is more stable than forcing camera + QR decode + Wi-Fi + fingerprint onto the same constrained MCU at once.
- Fingerprint matching stays on the R307, which is exactly where it belongs for this hardware.
- Development mode is designed around stable 5V USB power.
- Battery mode using only `18650 + TP4056` is documented as incomplete for full standalone use because TP4056 is only a charger/protection path, not a regulated 5V system rail.

## Repository Tree

```text
attendance-system/
  README.md
  backend/
    app.py
    auth.py
    config.py
    database.py
    models.py
    requirements.txt
    routes_attendance.py
    routes_auth.py
    routes_device.py
    routes_sessions.py
    routes_students.py
    seed_demo_data.py
    services_face.py
    services_qr.py
    services_reports.py
  firmware/
    esp32_cam_attendance/
      __init__.py
      api_client.py
      camera_service.py
      config.py
      fingerprint_service.py
      main.py
      models.py
      pins.py
      qr_service.py
      relay_service.py
      runtime.py
      state_machine.py
      storage_service.py
  web/
    static/
      css/styles.css
      js/dashboard.js
    templates/
      attendance_list.html
      base.html
      dashboard.html
      devices.html
      error.html
      login.html
      session_form.html
      sessions_list.html
      student_form.html
      students_list.html
  docs/
    api-spec.md
    architecture.md
    limitations.md
    testing.md
    wiring.md
```

## Final Architecture Decision

Sequential verification flow:

1. Admin logs in and creates a class session.
2. Backend generates a QR payload and dashboard QR image.
3. ESP32-CAM repeatedly captures frames while a session is active.
4. Backend decodes QR from uploaded JPEG frame.
5. If QR is valid, ESP32-CAM captures another frame for face verification.
6. Backend verifies face against enrolled students in that session's class.
7. ESP32-CAM prompts for fingerprint.
8. R307 performs local fingerprint search.
9. If face-matched student and fingerprint template match the same person, backend marks attendance with timestamp.
10. Relay pulses for success indication.

## Supported Development Environment

Backend:

- OS target: Ubuntu 22.04 or similar Linux environment
- Python: 3.10 or 3.11 recommended
- Database: SQLite
- Local dev transport: HTTP allowed
- Production recommendation: HTTPS behind reverse proxy

Firmware:

- Repo implementation: Python modules under `firmware/esp32_cam_attendance/`
- Hardware target: ESP32-CAM AI Thinker + R307
- Runtime model: Wi-Fi client, backend API client, camera capture wrapper, fingerprint service, relay service, and state machine
- Local development: the Python port can be reviewed and smoke-tested on desktop even when the physical device is unavailable

Python dependencies are pinned in [backend/requirements.txt](/C:/Users/Dipesh/Desktop/By%20Name%20New/Bibha/code/sketch_apr12c/attendance-system/backend/requirements.txt).

## Backend Setup

1. Open a terminal inside [backend](/C:/Users/Dipesh/Desktop/By%20Name%20New/Bibha/code/sketch_apr12c/attendance-system/backend).
2. Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set environment variables:

```bash
export SECRET_KEY="replace-this"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD_HASH="paste-werkzeug-password-hash"
export GITHUB_CLIENT_ID="your-github-oauth-app-client-id"
export GITHUB_CLIENT_SECRET="your-github-oauth-app-client-secret"
export GITHUB_REDIRECT_URI="http://127.0.0.1:5000/login/github/callback"
export GITHUB_ALLOWED_EMAILS="ybibha22@tbc.edu.np"
export DATABASE_URL="sqlite:///attendance.db"
export UPLOAD_DIR="uploads"
```

5. Create the database and seed demo records:

```bash
python seed_demo_data.py
```

6. Run the server:

```bash
python app.py
```

7. Open `http://127.0.0.1:5000/login`

If `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are set, the login page will also show a `Continue with GitHub` button.
Register the OAuth app callback URL as `http://127.0.0.1:5000/login/github/callback` for local development.

Default seeded demo values:

- Username: `admin`
- Device ID: `esp32cam-lab-01`
- Device key: `demo-device-key`
- Demo session token QR payload: `ATTEND:demo-session-token`

You should replace the admin hash before presentation use.

## Firmware Setup

1. Open [config.py](/C:/Users/Dipesh/Desktop/By%20Name%20New/Bibha/code/sketch_apr12c/attendance-system/firmware/esp32_cam_attendance/config.py) and set Wi-Fi SSID, password, backend base URL, device ID, and device API key for your environment.
2. If you want to avoid editing tracked source for each network change, copy [device_settings.json.example](/C:/Users/Dipesh/Desktop/By%20Name%20New/Bibha/code/sketch_apr12c/attendance-system/firmware/device_settings.json.example) to `firmware/device_settings.json` and put your live values there. The firmware will use that file if it exists.
3. Review [main.py](/C:/Users/Dipesh/Desktop/By%20Name%20New/Bibha/code/sketch_apr12c/attendance-system/firmware/esp32_cam_attendance/main.py) and [state_machine.py](/C:/Users/Dipesh/Desktop/By%20Name%20New/Bibha/code/sketch_apr12c/attendance-system/firmware/esp32_cam_attendance/state_machine.py) as the firmware entrypoint and sequential verification flow.
4. Match the configured `DEVICE_ID` and `DEVICE_API_KEY` with a registered backend device record.
5. Upload the files with [upload_to_esp32.bat](/C:/Users/Dipesh/Desktop/By%20Name%20New/Bibha/code/sketch_apr12c/attendance-system/firmware/upload_to_esp32.bat). If `firmware/device_settings.json` exists, the script uploads it automatically.

## ESP32-CAM Wiring Notes

1. Connect USB-to-TTL adapter:
   - `U0R` to adapter `TX`
   - `U0T` to adapter `RX`
   - `GND` to `GND`
   - `5V` to stable `5V`
2. Wire the R307 as follows:
   - `VCC` to `VIN / 5V`
   - `GND` to `GND`
   - `TX` to `GPIO12` / `IO12`
   - `RX` to `GPIO14` / `IO14`
3. Pull `GPIO0` to `GND` for flashing.
4. Press reset or power cycle the board.
5. After flashing your target firmware build, remove `GPIO0` from `GND`.
6. Press reset again to boot the device.

This firmware intentionally keeps the fingerprint sensor off the primary serial pins `GPIO1` and `GPIO3`, so upload/debug remains separate from the R307 UART link.

## Quick Demo Workflow

1. Start backend.
2. Seed demo data or create real students and sessions from dashboard.
3. Register at least one device record with the same `DEVICE_ID` and API key used in firmware.
4. Upload firmware and power ESP32-CAM from stable USB 5V.
5. Open dashboard, create a session, and activate it.
6. Show the session QR code to the ESP32-CAM.
7. Present enrolled face to the camera.
8. Place enrolled finger on R307.
9. Check relay pulse and attendance record creation.

## Security Notes

- Admin password verification prefers Werkzeug password hashes and only falls back to a plain-text password if no hash is configured.
- Device authentication uses `X-Device-Id` and `X-Device-Key`.
- Local development can run over HTTP.
- Production deployment should place Flask behind HTTPS or a reverse proxy.
- Fingerprint images are not stored in backend; only the matched R307 template ID is stored.
- Face images are stored only as uploaded reference images plus derived embeddings for prototype use.

## Known Practical Limits

- Face recognition accuracy depends heavily on lighting, camera angle, and good enrollment photos.
- `face_recognition` depends on `dlib`, which is easiest to install on Ubuntu and can be painful on Windows.
- ESP32-CAM is not a reliable platform for simultaneous on-device face recognition, QR decoding, and a rich dashboard. That is why this prototype offloads heavy work to the backend.
- Battery-only operation is not considered stable without an added 5V boost regulator.

## Requirement Coverage Matrix

| Requirement | Status | Notes |
|---|---|---|
| Sequential QR -> Face -> Fingerprint | Implemented | Handled by firmware state machine and backend APIs |
| Attendance timestamp storage | Implemented | Stored in SQLite `attendance_records` |
| Student registration workflow | Implemented | Dashboard student pages |
| Fingerprint enrollment workflow | Implemented | Backend queues command, device enrolls on R307 |
| Face enrollment workflow | Implemented | Upload image from dashboard |
| Session creation | Implemented | Dashboard session form |
| Session QR generation | Implemented | PNG QR endpoint and dashboard display |
| Basic secure admin login | Implemented | Hashed password check |
| Real-time-ish dashboard refresh | Partial | Manual refresh plus near-live device heartbeat data |
| Relay trigger on success | Implemented | Device pulses relay after successful attendance mark |
| Clear logs and error handling | Implemented | Serial logs, backend JSON errors, flash messages |
| Duplicate attendance rejection | Implemented | Rejected unless session explicitly allows duplicates |
| Attendance reports with filters | Implemented | Attendance page filters |
| CSV export | Implemented | Export endpoint |
| Simple charts | Not implemented | Skipped to prioritize hardware reliability |
| Device health page | Implemented | Devices page and dashboard summary |
| Retry logic and timeout logic | Implemented | Firmware timeouts, heartbeat, reconnect path |
| API authentication between device and backend | Implemented | API key per device |
| On-device face recognition | Not implemented | Intentionally offloaded to backend |
| On-device QR decode | Not implemented | Intentionally offloaded to backend |

## What To Improve If You Extend This Project

- Add a proper device registration UI.
- Add TLS termination with Nginx or Caddy.
- Add background tasks and audit logs.
- Add fingerprint template deletion and storage slot management.
- Add WebSocket or SSE updates for truly live dashboard refresh.
