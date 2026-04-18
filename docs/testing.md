# Testing Procedure

## Compile Validation

### Backend

1. Create Python virtual environment
2. Install requirements
3. Run `python app.py`
4. Confirm database initializes without import errors

### Firmware

1. Copy `config.example.h` to `config.h`
2. Fill Wi-Fi and backend settings
3. Select `AI Thinker ESP32-CAM`
4. Ensure PSRAM is enabled
5. Compile sketch in Arduino IDE

## Hardware Boot Test

1. Power ESP32-CAM from stable 5V USB
2. Open serial monitor at `115200`
3. Confirm boot counter and Wi-Fi logs appear
4. Confirm camera init succeeds
5. Confirm fingerprint sensor online message appears

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
