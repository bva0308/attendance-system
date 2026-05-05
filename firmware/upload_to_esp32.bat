@echo off
REM Upload full MicroPython firmware (camera + fingerprint) to ESP32-CAM via mpremote.
REM Usage from the firmware folder:
REM   upload_to_esp32.bat COM9

SET PORT=%1
IF "%PORT%"=="" (
    echo Usage: upload_to_esp32.bat COMx
    echo Example: upload_to_esp32.bat COM9
    exit /b 1
)

SET SRC=esp32_cam_attendance

echo Checking MicroPython REPL on %PORT% ...
mpremote connect %PORT% exec "print('ESP32-CAM REPL OK')"
IF ERRORLEVEL 1 (
    echo.
    echo ERROR: Could not enter MicroPython raw REPL on %PORT%.
    echo.
    echo For mpremote upload, the ESP32-CAM must be in NORMAL BOOT mode:
    echo   1. Remove IO0 -^> GND
    echo   2. Keep TTL 5V/GND/TX/RX connected
    echo   3. Press and release RST
    echo   4. Wait 3 seconds
    echo   5. Run this script again
    echo.
    echo Do NOT keep IO0 connected to GND when using mpremote.
    exit /b 1
)

echo.
echo Uploading FULL firmware (camera + fingerprint) to ESP32-CAM on %PORT% ...

mpremote connect %PORT% cp %SRC%\boot.py                :boot.py || exit /b 1
mpremote connect %PORT% cp %SRC%\config.py              :config.py || exit /b 1
mpremote connect %PORT% cp %SRC%\pins.py                :pins.py || exit /b 1
mpremote connect %PORT% cp %SRC%\models.py              :models.py || exit /b 1
mpremote connect %PORT% cp %SRC%\runtime.py             :runtime.py || exit /b 1
mpremote connect %PORT% cp %SRC%\camera_service.py      :camera_service.py || exit /b 1
mpremote connect %PORT% cp %SRC%\fingerprint_service.py :fingerprint_service.py || exit /b 1
mpremote connect %PORT% cp %SRC%\r307s.py               :r307s.py || exit /b 1
mpremote connect %PORT% cp %SRC%\relay_service.py       :relay_service.py || exit /b 1
mpremote connect %PORT% cp %SRC%\api_client.py          :api_client.py || exit /b 1
mpremote connect %PORT% cp %SRC%\qr_service.py          :qr_service.py || exit /b 1
mpremote connect %PORT% cp %SRC%\storage_service.py     :storage_service.py || exit /b 1
mpremote connect %PORT% cp %SRC%\state_machine.py       :state_machine.py || exit /b 1
mpremote connect %PORT% cp %SRC%\main.py                :main.py || exit /b 1

IF EXIST device_settings.json (
    echo Uploading device_settings.json override...
    mpremote connect %PORT% cp device_settings.json :device_settings.json || exit /b 1
) ELSE (
    echo device_settings.json not found, using values baked into config.py
)

echo.
echo Resetting device...
mpremote connect %PORT% reset

echo Upload complete.
