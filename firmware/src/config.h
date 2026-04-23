#pragma once

// ── I2S / INMP441 ────────────────────────────────────────────────────────────
#define I2S_SCK_PIN       26    // Bit clock
#define I2S_WS_PIN        25    // Word select (LRCK)
#define I2S_SD_PIN        33    // Serial data (SD)
#define SAMPLE_RATE       16000
#define CAPTURE_MS        1000  // Capture window per POST
#define I2S_DMA_BUF_COUNT 8
#define I2S_DMA_BUF_LEN  512

// ── Actuators ─────────────────────────────────────────────────────────────────
#define LED_PIN           5     // WS2812B data pin
#define LED_COUNT         1     // Number of LEDs on the strip
#define VIBRO_PIN         18    // Vibration motor PWM pin
#define VIBRO_CHANNEL     0     // LEDC channel
#define VIBRO_FREQ_HZ     1000
#define VIBRO_RESOLUTION  8     // 8-bit duty cycle

// ── Alert timings ─────────────────────────────────────────────────────────────
#define LED_HOLD_MS       3000  // How long to hold alert colour
#define VIBRO_PULSE_MS    200   // Single pulse duration

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
