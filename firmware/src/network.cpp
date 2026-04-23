#include "network.h"
#include "config.h"

#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>

// ── helpers ───────────────────────────────────────────────────────────────────

static bool http_begin_url(HTTPClient& http, const char* backend_url, const char* path) {
    char url[256];
    snprintf(url, sizeof(url), "%s%s", backend_url, path);
    return http.begin(url);
}

// ── classify ──────────────────────────────────────────────────────────────────

ClassifyResult network_classify(const char* backend_url,
                                int         device_id,
                                const void* pcm_bytes,
                                size_t      byte_count) {
    ClassifyResult result{};

    char path[64];
    snprintf(path, sizeof(path), "/api/audio/classify?device_id=%d", device_id);

    for (int attempt = 0; attempt < HTTP_MAX_RETRIES; attempt++) {
        HTTPClient http;
        http.setTimeout(HTTP_TIMEOUT_MS);

        if (!http_begin_url(http, backend_url, path)) {
            delay(HTTP_RETRY_DELAY);
            continue;
        }

        http.addHeader("Content-Type", "application/octet-stream");
        int code = http.POST((uint8_t*)pcm_bytes, byte_count);

        if (code == 200) {
            String body = http.getString();
            http.end();

            JsonDocument doc;
            if (deserializeJson(doc, body) == DeserializationError::Ok) {
                strlcpy(result.class_name,  doc["class_name"] | "unknown", sizeof(result.class_name));
                strlcpy(result.led_color,   doc["led_color"]  | "#FFFFFF", sizeof(result.led_color));
                strlcpy(result.vibration,   doc["vibration"]  | "none",    sizeof(result.vibration));
                result.confidence = doc["confidence"] | 0.0f;
                result.ok = true;
            }
            return result;
        }

        http.end();
        Serial.printf("[network] classify attempt %d failed, HTTP %d\n", attempt + 1, code);
        delay(HTTP_RETRY_DELAY);
    }

    strlcpy(result.class_name, "unknown", sizeof(result.class_name));
    return result;
}

// ── register device ───────────────────────────────────────────────────────────

int network_register_device(const char* backend_url,
                            const char* device_name,
                            const char* room) {
    JsonDocument doc;
    doc["name"] = device_name;
    doc["room"] = room;

    String body;
    serializeJson(doc, body);

    HTTPClient http;
    http.setTimeout(HTTP_TIMEOUT_MS);

    if (!http_begin_url(http, backend_url, "/api/devices/register")) {
        return -1;
    }

    http.addHeader("Content-Type", "application/json");
    int code = http.POST(body);

    if (code == 200 || code == 201) {
        String resp = http.getString();
        http.end();

        JsonDocument resp_doc;
        if (deserializeJson(resp_doc, resp) == DeserializationError::Ok) {
            return resp_doc["id"] | -1;
        }
    }

    Serial.printf("[network] device registration failed, HTTP %d\n", code);
    http.end();
    return -1;
}
