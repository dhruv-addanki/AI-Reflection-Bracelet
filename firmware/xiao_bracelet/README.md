# XIAO Bracelet Firmware

Arduino-based firmware scaffold for the XIAO ESP32S3 Sense that separates:

- local recording
- Wi-Fi connectivity
- JSON connectivity testing
- multipart WAV upload to the FastAPI backend

## What is implemented

- Wi-Fi connect and reconnect logging
- NTP time sync attempt
- button-driven state machine
- `/test-upload` JSON POST
- `/sessions/upload` multipart WAV upload
- fake-recorder mode for transport testing when the real recorder hooks are not yet wired

## What you need to wire

Edit [wifi_config.h](/Users/dhruv/Projects/AI Reflection Bracelet/firmware/xiao_bracelet/wifi_config.h):

- `WIFI_SSID`
- `WIFI_PASSWORD`
- `API_HOST`
- `API_PORT`
- `USER_ID`
- `DEVICE_ID`
- `BUTTON_PIN`
- `SD_CS_PIN`

## Real recorder integration

The sketch currently supports a fake recorder path so Wi-Fi and upload can be tested from this repo even though the proven local recorder code is not in the repo yet.

When you are ready to wire the real recording loop:

1. set `BRACELET_FAKE_RECORDER = false`
2. replace the TODO implementations in:
   - `beginRealRecorder(...)`
   - `serviceRealRecorder()`
   - `stopRealRecorder()`

Those hook points are intentionally the only places that should touch your hardware-specific capture logic.

## Backend flow

1. Stop recording
2. Finalize the WAV on SD
3. `POST /test-upload` with metadata
4. `POST /sessions/upload` multipart with `audio_file`
5. Keep file on SD if upload fails

## Notes

- The backend currently accepts multipart bracelet uploads on `/sessions/upload`.
- `/test-upload` is temporary and meant only for connectivity verification.
- The sketch prints detailed Serial logs for Wi-Fi, test POSTs, upload attempts, and failures.
