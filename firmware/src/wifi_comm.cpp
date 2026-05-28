#include "wifi_comm.h"
#include "config.h"
#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>

void wifi_init() {
    Serial.printf("[wifi] Connecting to %s", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\n[wifi] Connected. IP: %s\n", WiFi.localIP().toString().c_str());
}

ClassifyResult wifi_classify(const void* pcm_bytes, size_t byte_count) {
    ClassifyResult result = {};

    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[wifi] Not connected — skipping classify");
        return result;
    }

    HTTPClient http;
    String url = String(BACKEND_URL) + "/api/audio/classify?device_id=" + String(WIFI_DEVICE_ID);
    http.begin(url);
    http.addHeader("Content-Type", "application/octet-stream");
    http.setTimeout(10000);

    int status = http.POST((uint8_t*)pcm_bytes, byte_count);
    if (status != 200) {
        Serial.printf("[wifi] Backend returned HTTP %d\n", status);
        http.end();
        return result;
    }

    String body = http.getString();
    http.end();

    JsonDocument doc;
    if (deserializeJson(doc, body) != DeserializationError::Ok) {
        Serial.println("[wifi] Failed to parse JSON response");
        return result;
    }

    const char* vibration = doc["vibration"] | doc["vibration_pattern"] | "none";
    strlcpy(result.class_name, doc["class_name"] | "unknown", sizeof(result.class_name));
    result.confidence = doc["confidence"] | 0.0f;
    strlcpy(result.led_color, doc["led_color"] | "#000000", sizeof(result.led_color));
    strlcpy(result.vibration, vibration, sizeof(result.vibration));
    result.ok = true;

    Serial.printf("[wifi] class=%s confidence=%.2f\n", result.class_name, result.confidence);
    return result;
}
