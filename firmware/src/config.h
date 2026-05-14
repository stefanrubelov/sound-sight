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
#define LED_PIN           16    // WS2812B data pin (DIN via 330 Ω resistor)
#define LED_COUNT         16    // Number of LEDs to address on the strip

// ── Alert timings ─────────────────────────────────────────────────────────────
#define LED_HOLD_MS       3000  // How long to hold alert colour

// ── Serial protocol ──────────────────────────────────────────────────────────
#define SERIAL_BAUD              921600
#define FRAME_MAGIC_TX_0         0xAA   // ESP32 → Bridge: PCM frame
#define FRAME_MAGIC_TX_1         0x55
#define FRAME_MAGIC_RX_0         0xBB   // Bridge → ESP32: classification result
#define FRAME_MAGIC_RX_1         0x66
#define SERIAL_RESPONSE_TIMEOUT_MS 5000 // Max wait for bridge response
