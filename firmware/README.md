# Firmware

ESP32 firmware for SoundSight audio nodes.

## Hardware

- ESP32 WROOM (or S3)
- INMP441 I2S digital microphone
- WS2812B LED strip
- Vibration motor (via MOSFET)
- Optional: SSD1306 OLED

## Build & upload

```bash
pio run -t upload
pio device monitor
```

## Wiring

TBD — added in Phase 2.
