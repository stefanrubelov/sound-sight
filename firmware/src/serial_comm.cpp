#include "serial_comm.h"
#include "config.h"
#include <Arduino.h>
#include <ArduinoJson.h>

ClassifyResult serial_classify(const void* pcm_bytes, size_t byte_count) {
    ClassifyResult result = {};

    // Send framed PCM: [0xAA][0x55][LEN_HIGH][LEN_LOW][PCM...][CHECKSUM]
    Serial.write(FRAME_MAGIC_TX_0);
    Serial.write(FRAME_MAGIC_TX_1);
    Serial.write((uint8_t)(byte_count >> 8));
    Serial.write((uint8_t)(byte_count & 0xFF));

    const uint8_t* bytes = (const uint8_t*)pcm_bytes;
    Serial.write(bytes, byte_count);

    uint8_t checksum = 0;
    for (size_t i = 0; i < byte_count; i++) checksum ^= bytes[i];
    Serial.write(checksum);
    Serial.flush();

    // Wait for response: [0xBB][0x66][JSON\n]
    unsigned long deadline = millis() + SERIAL_RESPONSE_TIMEOUT_MS;
    uint8_t state = 0;  // 0=seek_magic0, 1=seek_magic1, 2=read_json

    char json_buf[256];
    size_t json_len = 0;

    while (millis() < deadline) {
        if (!Serial.available()) continue;

        uint8_t b = Serial.read();

        if (state == 0) {
            if (b == FRAME_MAGIC_RX_0) state = 1;
        } else if (state == 1) {
            if (b == FRAME_MAGIC_RX_1) state = 2;
            else state = (b == FRAME_MAGIC_RX_0) ? 1 : 0;
        } else {
            if (b == '\n' || json_len >= sizeof(json_buf) - 1) {
                json_buf[json_len] = '\0';
                break;
            }
            json_buf[json_len++] = (char)b;
        }
    }

    if (state != 2 || json_len == 0) return result;

    JsonDocument doc;
    if (deserializeJson(doc, json_buf) != DeserializationError::Ok) return result;

    strlcpy(result.class_name, doc["class_name"] | "unknown", sizeof(result.class_name));
    result.confidence = doc["confidence"] | 0.0f;
    strlcpy(result.led_color, doc["led_color"] | "#000000", sizeof(result.led_color));
    strlcpy(result.vibration, doc["vibration"] | "none", sizeof(result.vibration));
    result.ok = true;
    return result;
}
