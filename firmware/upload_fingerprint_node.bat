@echo off
REM Upload MicroPython fingerprint-node firmware to a normal ESP32 dev board.
REM Usage from the firmware folder:
REM   upload_fingerprint_node.bat COM6

SET PORT=%1
IF "%PORT%"=="" (
    echo Usage: upload_fingerprint_node.bat COMx
    echo Example: upload_fingerprint_node.bat COM6
    exit /b 1
)

SET SRC=esp32_fingerprint_node

echo Checking MicroPython REPL on %PORT% ...
mpremote connect %PORT% exec "print('FINGERPRINT NODE REPL OK')"
IF ERRORLEVEL 1 (
    echo.
    echo ERROR: Could not enter MicroPython raw REPL on %PORT%.
    echo Hold BOOT, tap EN/RST, release BOOT, then try again.
    echo If this still fails, erase and flash ESP32_GENERIC-v1.24.1.bin first.
    exit /b 1
)

echo.
echo Uploading fingerprint-node firmware to %PORT% ...

mpremote connect %PORT% cp %SRC%\config.py              :config.py || exit /b 1
mpremote connect %PORT% cp %SRC%\runtime.py             :runtime.py || exit /b 1
mpremote connect %PORT% cp %SRC%\r307s.py               :r307s.py || exit /b 1
mpremote connect %PORT% cp %SRC%\fingerprint_service.py :fingerprint_service.py || exit /b 1
mpremote connect %PORT% cp %SRC%\api_client.py          :api_client.py || exit /b 1
mpremote connect %PORT% cp %SRC%\main.py                :main.py || exit /b 1
mpremote connect %PORT% cp %SRC%\boot.py                :boot.py || exit /b 1

IF EXIST fingerprint_settings.json (
    echo Uploading fingerprint_settings.json override...
    mpremote connect %PORT% cp fingerprint_settings.json :fingerprint_settings.json || exit /b 1
)

echo.
echo Resetting fingerprint node...
mpremote connect %PORT% reset

echo Upload complete.
