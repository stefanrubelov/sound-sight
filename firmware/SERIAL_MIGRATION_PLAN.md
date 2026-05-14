# SoundSight — WiFi to USB Serial Migration Plan

Replace WiFi HTTP communication with USB serial for demo use. The ESP32 stays connected to the laptop via USB cable. A Python bridge script on the laptop relays audio data to the backend and classification results back.

---

## Architecture

```
ESP32 (FireBeetle)              Laptop
┌──────────────┐    USB Serial    ┌─────────────────┐    HTTP POST     ┌──────────────┐
│ Capture audio ├───────────────►│ serial_bridge.py ├──────────────►  │ FastAPI       │
│ via I2S       │                │                  │                  │ /api/audio/   │
│               │◄───────────────┤                  │◄──────────────  │ classify      │
│ Drive LEDs    │  JSON response │                  │  JSON response  │              │
└──────────────┘                └─────────────────┘                  └──────────────┘
```

Backend code is **unchanged**. The bridge script handles the translation.

---

## Serial Protocol

**Baud rate: 921600** (32KB PCM in ~0.35s, leaving room for round-trip)

### ESP32 → Bridge (PCM audio frame)

```
[0xAA][0x55][LEN_HIGH][LEN_LOW][PCM_BYTES...][CHECKSUM]
```

- Magic: `0xAA 0x55` (distinguishes binary frames from ASCII debug prints)
- Length: 2 bytes big-endian uint16 (value = 32000 for 1-second capture)
- PCM data: `LEN` bytes of raw 16-bit signed PCM
- Checksum: 1 byte, XOR of all PCM bytes

Any bytes that are NOT part of a frame (i.e., don't start with `0xAA 0x55`) are debug text — the bridge prints them to stdout prefixed with `[ESP32]`.

### Bridge → ESP32 (classification result)

```
[0xBB][0x66][JSON_LINE\n]
```

- Magic: `0xBB 0x66`
- JSON: single line terminated by `\n`, fields: `class_name`, `confidence`, `led_color`, `vibration`

Example: `\xBB\x66{"class_name":"fire_alarm","confidence":0.95,"led_color":"#FF1E00","vibration":"continuous"}\n`

---

## File Changes

### DELETE these files (no longer needed)

- `firmware/src/network.h`
- `firmware/src/network.cpp`
- `firmware/src/config_portal.h`
- `firmware/src/config_portal.cpp`

### MODIFY `firmware/platformio.ini`

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 921600                          ; was 115200
lib_deps =
  fastled/FastLED@^3.7.0
  bblanchon/ArduinoJson@^7.2.0
                                                 ; REMOVE WiFiManager line
```

### MODIFY `firmware/src/config.h`

Remove everything below the `// Alert timings` section (NVS, Networking, Config portal defines — lines 19–35). Replace with:

```c
// ── Serial protocol ──────────────────────────────────────────────────────────
#define SERIAL_BAUD              921600
#define FRAME_MAGIC_TX_0         0xAA   // ESP32 → Bridge: PCM frame
#define FRAME_MAGIC_TX_1         0x55
#define FRAME_MAGIC_RX_0         0xBB   // Bridge → ESP32: classification result
#define FRAME_MAGIC_RX_1         0x66
#define SERIAL_RESPONSE_TIMEOUT_MS 5000 // Max wait for bridge response
```

Keep lines 1–17 (I2S, actuators, alert timings) exactly as-is.

### CREATE `firmware/src/serial_comm.h`

```cpp
#pragma once
#include <stddef.h>
#include <stdint.h>

struct ClassifyResult {
    char  class_name[32];
    float confidence;
    char  led_color[16];
    char  vibration[16];
    bool  ok;                // false if timeout or parse error
};

// Send a framed PCM buffer over Serial and wait for the bridge's JSON response.
ClassifyResult serial_classify(const void* pcm_bytes, size_t byte_count);
```

### CREATE `firmware/src/serial_comm.cpp`

Implement `serial_classify()`:

1. Write magic bytes `0xAA, 0x55`
2. Write length as 2-byte big-endian uint16 (`byte_count`)
3. Write all PCM bytes via `Serial.write()`
4. Compute XOR checksum over all PCM bytes, write 1 byte
5. `Serial.flush()` to ensure all bytes are sent
6. Wait up to `SERIAL_RESPONSE_TIMEOUT_MS` for response:
   - Read bytes looking for magic `0xBB, 0x66`
   - Read until `\n` to get the JSON line
   - Parse JSON with ArduinoJson (`deserializeJson`)
   - Extract `class_name`, `confidence`, `led_color`, `vibration` into ClassifyResult
   - Return `ok = true`
7. On timeout or parse failure, return `ok = false`

Important: no `Serial.println()` debug output between the magic header write and `Serial.flush()` — it would corrupt the frame.

### MODIFY `firmware/src/main.cpp`

**Remove includes:**
- `#include "config_portal.h"`
- `#include "network.h"`

**Add include:**
- `#include "serial_comm.h"`

**Remove globals:**
- `static DeviceConfig g_cfg;`

**Rewrite `setup()`:**
```cpp
void setup() {
    Serial.begin(SERIAL_BAUD);
    Serial.println("[main] SoundSight booting (serial mode)...");
    actuators_init();
    audio_init();
    Serial.println("[main] Ready.");
}
```

Remove: `pinMode(RESET_BUTTON_PIN, ...)`, all config_load/config_portal_run/config_save logic, `network_register_device` block.

**Rewrite `loop()`:**
```cpp
void loop() {
    actuators_tick();

    size_t bytes = audio_capture(g_pcm, SAMPLE_RATE);
    if (bytes == 0) {
        Serial.println("[main] audio_capture returned 0 -- skipping");
        return;
    }

    float rms = audio_rms(g_pcm, bytes / sizeof(int16_t));
    Serial.printf("[main] RMS=%.1f\n", rms);

    if (rms < 200.0f) return;

    ClassifyResult result = serial_classify(g_pcm, bytes);

    Serial.printf("[main] class=%s confidence=%.2f ok=%d\n",
                  result.class_name, result.confidence, result.ok);

    if (!result.ok) return;

    AlertProfile profile = get_alert_profile(result.class_name);
    if (strcmp(profile.severity, "none") != 0) {
        actuators_alert(profile);
    }
}
```

Remove: `config_check_reset()` call. Replace `network_classify(g_cfg.backend_url, g_cfg.device_id, g_pcm, bytes)` with `serial_classify(g_pcm, bytes)`.

### CREATE `scripts/serial_bridge.py`

Python script that bridges USB serial to the FastAPI backend.

**CLI args:**
- `--port` (required) — e.g., `/dev/cu.wchusbserial1130`
- `--baud` (default 921600)
- `--backend` (default `http://localhost:8000`)
- `--device-id` (default 1)

**Logic (state machine):**

```
State: IDLE
  - Read bytes from serial
  - If byte == 0xAA → go to MAGIC_1 state
  - Otherwise, buffer as ASCII debug text, print lines to stdout as "[ESP32] ..."

State: MAGIC_1
  - If next byte == 0x55 → go to HEADER state
  - Otherwise, back to IDLE (was not a real frame)

State: HEADER
  - Read 2 bytes → length (big-endian uint16)
  - Go to PAYLOAD state

State: PAYLOAD
  - Read exactly `length` bytes of PCM data (loop until all received, with timeout)
  - Go to CHECKSUM state

State: CHECKSUM
  - Read 1 byte
  - Verify XOR checksum of PCM bytes
  - If mismatch: log warning, go to IDLE
  - If valid:
    1. POST PCM bytes to {backend}/api/audio/classify?device_id={device_id}
       Content-Type: application/octet-stream
       Timeout: 10 seconds
    2. On HTTP 200: parse JSON response
    3. Build response JSON: {"class_name": "...", "confidence": ..., "led_color": "...", "vibration": "..."}
       NOTE: the backend may return `vibration_pattern` — map it to `vibration` for firmware compatibility
    4. Send over serial: bytes(0xBB, 0x66) + json_string.encode() + b'\n'
    5. On HTTP error: send back default unknown response
    6. Log result to stdout
  - Go to IDLE
```

**Top-of-file comment:** Note that `pio device monitor` and the bridge script cannot use the serial port simultaneously. Close the bridge before uploading new firmware.

**Handle `KeyboardInterrupt`:** close serial port cleanly.

### CREATE `scripts/requirements-bridge.txt`

```
pyserial>=3.5
requests>=2.28
```

---

## Files That Stay Unchanged

- `firmware/src/audio.h` / `audio.cpp` — untouched
- `firmware/src/actuators.h` / `actuators.cpp` — untouched
- `firmware/src/event_map.h` — untouched
- All backend code — untouched

---

## Implementation Order

1. `firmware/src/config.h` — remove old defines, add serial protocol constants
2. Delete `firmware/src/config_portal.h` and `config_portal.cpp`
3. Delete `firmware/src/network.h` and `network.cpp`
4. Create `firmware/src/serial_comm.h`
5. Create `firmware/src/serial_comm.cpp`
6. Modify `firmware/src/main.cpp` — update includes, simplify setup/loop
7. Modify `firmware/platformio.ini` — update baud, remove WiFiManager dep
8. Create `scripts/serial_bridge.py`
9. Create `scripts/requirements-bridge.txt`

---

## Testing

1. **Upload firmware:** `pio run --target upload`
2. **Install bridge deps:** `pip install -r scripts/requirements-bridge.txt`
3. **Start the FastAPI backend:** `cd backend && uvicorn app.main:app`
4. **Run the bridge:** `python scripts/serial_bridge.py --port /dev/cu.wchusbserial1130 --backend http://localhost:8000`
5. **Make noise near the mic.** You should see:
   - `[ESP32] [main] RMS=XXX` in bridge stdout (debug text forwarded)
   - `Sending 32000 bytes to backend...` (bridge log)
   - `Classification: fire_alarm (0.95)` (bridge log)
   - LEDs light up on the strip

---

## Potential Issues

- **Baud 921600 not supported by CH340:** The FireBeetle's USB-serial chip may not support 921600. If you get garbage output, fall back to 460800 (change in both `config.h` and `--baud` arg). At 460800, PCM transfer takes ~0.7s — still workable.
- **Serial buffer overflow:** ESP32 UART TX FIFO is 128 bytes. `Serial.write()` for 32KB blocks until sent — this is fine since the ESP32 has nothing else to do during transmission.
- **Port conflict:** The bridge script and `pio device monitor` cannot run simultaneously. Close the bridge before flashing.
