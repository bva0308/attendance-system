# Testing Procedure

## Compile Validation

### Backend

1. Create Python virtual environment
2. Install requirements
3. Run `python app.py`
4. Confirm database initializes without import errors

### Firmware

1. Review `firmware/esp32_cam_attendance/config.py`
2. Optionally copy `firmware/device_settings.json.example` to `firmware/device_settings.json`
3. Set the Wi-Fi SSID, password, backend URL, device ID, and API key
4. Upload files with `upload_to_esp32.bat COMx`
5. Confirm the ESP32 boots into `main.py`

## Hardware Boot Test

1. Power ESP32-CAM from stable 5V USB
2. Open serial monitor at `115200`
3. Confirm boot counter and Wi-Fi logs appear
4. Confirm camera init succeeds
5. Confirm fingerprint sensor logs either `sensor online` or `sensor not detected`

## Network Validation

1. On the backend PC, run `ipconfig`
2. Confirm the Wi-Fi IPv4 address matches the subnet the ESP32 joins
3. Set `backend_base_url` to `http://<pc-ip>:5000`
4. Start Flask with `python app.py` from the `backend/` folder
5. Confirm the device heartbeat appears on the dashboard or `/devices` page

If the ESP32 receives an address like `192.168.18.x` while the PC is on `192.168.2.x`, the board is on a different network and will not reach the backend until both are on the same LAN.

## Verification Checklist

### Wi-Fi Test

- Device connects and prints IP address
- Dashboard device page updates `last seen`

### Camera Capture Test

- Device reaches `WAIT_QR`
- Backend receives QR verify requests without crashing

### QR Verification Test

- Show active session QR to camera
- Confirm session accepted
- Try random or expired QR and confirm rejection

### Face Verification Test

- Enroll face for a student
- Present enrolled face and confirm match
- Present wrong face and confirm rejection
- Test poor lighting to see realistic sensitivity

### Fingerprint Enrollment Test

- Queue fingerprint enrollment from dashboard
- Present same finger twice
- Confirm template ID saved in backend

### Fingerprint Match Test

- Present enrolled finger after successful face match
- Confirm attendance completes
- Present wrong finger and confirm rejection

### Relay Activation Test

- Confirm relay pulses after successful attendance only
- Confirm no pulse on failure paths

### Duplicate Attendance Test

- Attempt same student twice in same session
- Confirm second attempt is rejected unless duplicates are enabled

### Timeout Test

- Do not present finger after face verification
- Confirm timeout and recovery to `WAIT_QR`

### Backend Offline Test

- Stop Flask backend while device is running
- Confirm device falls into recovery behavior and logs errors

## Expected Performance

- QR step: about 1 to 2.5 seconds depending on frame quality and network
- Face verification: about 1 to 3 seconds depending on backend hardware
- Fingerprint verification: usually under 2 seconds after finger placement

A full successful pass is realistically around 3 to 7 seconds, not guaranteed under 3 seconds in every environment.
