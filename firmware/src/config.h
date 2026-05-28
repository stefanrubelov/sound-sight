#pragma once

// ── I2S / INMP441 ────────────────────────────────────────────────────────────
#define I2S_SCK_PIN       14    // Bit clock
#define I2S_WS_PIN        25    // Word select (LRCK) — D2 on FireBeetle 2
#define I2S_SD_PIN        34    // Serial data (SD) — GPIO34/A2 on FireBeetle
#define SAMPLE_RATE       16000
#define CAPTURE_MS        1000  // Capture window per POST
#define I2S_DMA_BUF_COUNT 8
#define I2S_DMA_BUF_LEN  512

// ── Actuators ─────────────────────────────────────────────────────────────────
#define LED_PIN           13    // WS2812B data pin (DIN via 330 Ω resistor)
#define LED_COUNT         60    // Number of LEDs to address on the strip

// ── Alert timings ─────────────────────────────────────────────────────────────
#define LED_HOLD_MS       3000  // How long to hold alert colour
#define MIN_CONFIDENCE    0.10f // Minimum confidence to trigger an alert (backend handles per-class filtering)

// ── Transport selection ───────────────────────────────────────────────────────
// Uncomment ONE of the following lines before flashing.
// TRANSPORT_WIFI  → ESP32 connects to WiFi and POSTs directly to the backend.
// TRANSPORT_SERIAL → ESP32 uses USB serial + scripts/serial_bridge.py (default).
#define TRANSPORT_WIFI
// #define TRANSPORT_SERIAL

// ── WiFi / backend (used only when TRANSPORT_WIFI is defined) ─────────────────
#define WIFI_SSID       "YourSSID"
#define WIFI_PASSWORD   "YourPassword"
#define BACKEND_URL     "http://192.168.1.100:8000"  // backend IP on the same network
#define WIFI_DEVICE_ID  1

// ── Serial protocol ──────────────────────────────────────────────────────────
#define SERIAL_BAUD              921600
#define FRAME_MAGIC_TX_0         0xAA   // ESP32 → Bridge: PCM frame
#define FRAME_MAGIC_TX_1         0x55
#define FRAME_MAGIC_RX_0         0xBB   // Bridge → ESP32: classification result
#define FRAME_MAGIC_RX_1         0x66
#define SERIAL_RESPONSE_TIMEOUT_MS 5000 // Max wait for bridge response
