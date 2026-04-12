@echo off
REM Upload MicroPython firmware files to ESP32 via mpremote
REM Usage: upload_to_esp32.bat COM3
REM   (replace COM3 with your actual port, e.g. COM4, COM5)

SET PORT=%1
IF "%PORT%"=="" (
    echo Usage: upload_to_esp32.bat COMx
    echo Example: upload_to_esp32.bat COM3
    pause
    exit /b 1
)

SET SRC=esp32_cam_attendance

echo Uploading firmware to ESP32 on %PORT% ...

mpremote connect %PORT% cp %SRC%\boot.py             :boot.py
mpremote connect %PORT% cp %SRC%\config.py           :config.py
mpremote connect %PORT% cp %SRC%\pins.py             :pins.py
mpremote connect %PORT% cp %SRC%\models.py           :models.py
mpremote connect %PORT% cp %SRC%\runtime.py          :runtime.py
mpremote connect %PORT% cp %SRC%\r307s.py            :r307s.py
mpremote connect %PORT% cp %SRC%\fingerprint_service.py :fingerprint_service.py
mpremote connect %PORT% cp %SRC%\camera_service.py   :camera_service.py
mpremote connect %PORT% cp %SRC%\relay_service.py    :relay_service.py
mpremote connect %PORT% cp %SRC%\api_client.py       :api_client.py
mpremote connect %PORT% cp %SRC%\qr_service.py       :qr_service.py
mpremote connect %PORT% cp %SRC%\storage_service.py  :storage_service.py
mpremote connect %PORT% cp %SRC%\state_machine.py    :state_machine.py
mpremote connect %PORT% cp %SRC%\main.py             :main.py

IF EXIST device_settings.json (
    echo Uploading device_settings.json override...
    mpremote connect %PORT% cp device_settings.json  :device_settings.json
) ELSE (
    echo device_settings.json not found, using values baked into config.py
)

echo.
echo Done! Resetting device...
mpremote connect %PORT% reset

echo Upload complete. Open serial monitor to see boot output.
pause
