#pragma once

// ── I2S / INMP441 ────────────────────────────────────────────────────────────
#define I2S_SCK_PIN       14    // Bit clock
#define I2S_WS_PIN        15    // Word select (LRCK)
#define I2S_SD_PIN        32    // Serial data (SD)
#define SAMPLE_RATE       16000
#define CAPTURE_MS        1000  // Capture window per POST
#define I2S_DMA_BUF_COUNT 8
#define I2S_DMA_BUF_LEN  512

// ── Actuators ─────────────────────────────────────────────────────────────────
#define LED_PIN           16    // WS2812B data pin (DIN via 330 Ω resistor)
#define LED_COUNT         16    // Number of LEDs to address on the strip

// ── Alert timings ─────────────────────────────────────────────────────────────
#define LED_HOLD_MS       3000  // How long to hold alert colour

// ── NVS namespace ─────────────────────────────────────────────────────────────
#define NVS_NAMESPACE     "soundsight"
#define NVS_KEY_BACKEND   "backend_url"
#define NVS_KEY_DEV_NAME  "device_name"
#define NVS_KEY_ROOM      "room"
#define NVS_KEY_DEV_ID    "device_id"

// ── Networking ────────────────────────────────────────────────────────────────
#define HTTP_TIMEOUT_MS   5000
#define HTTP_MAX_RETRIES  3
#define HTTP_RETRY_DELAY  1000

// ── Config portal ─────────────────────────────────────────────────────────────
#define PORTAL_AP_NAME    "SoundSight-Setup"
#define PORTAL_TIMEOUT_S  180   // AP mode times out after 3 min if no connection
#define RESET_BUTTON_PIN  0     // GPIO0 (BOOT button on most devkits)
#define RESET_HOLD_MS     3000  // Hold for 3 s to re-enter config mode
