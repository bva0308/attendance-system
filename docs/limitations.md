# Known Limitations

## Hardware Constraints

- ESP32-CAM has a tight GPIO budget once the camera is active
- microSD is intentionally not used to keep UART and relay mapping practical
- Battery-only operation is not stable without extra power hardware

## Face Recognition Constraints

- Uses backend-side `face_recognition`, which depends on `dlib`
- Installation is easiest on Ubuntu and may be difficult on some Windows setups
- Accuracy is affected by lighting, angle, occlusion, and enrollment image quality

## Fingerprint Constraints

- Prototype uses simple `templateCount + 1` slot allocation during enrollment
- Template deletion and compaction are not implemented
- Sensor capacity limits must be managed manually in larger deployments

## Dashboard Constraints

- Real-time updates are near-live, not true push updates
- No charting library is included because it was deprioritized in favor of hardware reliability

## Security Constraints

- Device auth uses shared API key headers, which is acceptable for prototype scope
- Local HTTP is allowed for development only
- No per-student consent workflow or advanced privacy governance is claimed

## Honesty Notes

- This repository does not claim robust offline operation
- It does not claim production-grade anti-spoofing for face recognition
- It does not claim enterprise-scale multi-device concurrency tuning
- It does not claim that TP4056 alone is sufficient for regulated 5V standalone use
