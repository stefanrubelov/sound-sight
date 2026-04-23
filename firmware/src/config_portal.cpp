#include "config_portal.h"
#include "config.h"

#include <Arduino.h>
#include <Preferences.h>
#include <WiFiManager.h>

// ── NVS helpers ───────────────────────────────────────────────────────────────

bool config_load(DeviceConfig& out) {
    Preferences prefs;
    prefs.begin(NVS_NAMESPACE, /*readOnly=*/true);

    bool valid = prefs.isKey(NVS_KEY_BACKEND);
    if (valid) {
        prefs.getString(NVS_KEY_BACKEND,  out.backend_url,  sizeof(out.backend_url));
        prefs.getString(NVS_KEY_DEV_NAME, out.device_name,  sizeof(out.device_name));
        prefs.getString(NVS_KEY_ROOM,     out.room,         sizeof(out.room));
        out.device_id = prefs.getInt(NVS_KEY_DEV_ID, 0);
    }

    prefs.end();
    return valid;
}

void config_save(const DeviceConfig& cfg) {
    Preferences prefs;
    prefs.begin(NVS_NAMESPACE, /*readOnly=*/false);
    prefs.putString(NVS_KEY_BACKEND,  cfg.backend_url);
    prefs.putString(NVS_KEY_DEV_NAME, cfg.device_name);
    prefs.putString(NVS_KEY_ROOM,     cfg.room);
    prefs.putInt(NVS_KEY_DEV_ID,      cfg.device_id);
    prefs.end();
}

void config_erase() {
    Preferences prefs;
    prefs.begin(NVS_NAMESPACE, false);
    prefs.clear();
    prefs.end();
}

// ── Config portal ─────────────────────────────────────────────────────────────

void config_portal_run(DeviceConfig& cfg) {
    WiFiManager wm;
    wm.setConfigPortalTimeout(PORTAL_TIMEOUT_S);

    // Custom parameters shown in the captive portal form
    WiFiManagerParameter p_backend("backend", "Backend URL",
                                   "http://192.168.1.100:8000", 127);
    WiFiManagerParameter p_name("devname", "Device name", "Living Room", 63);
    WiFiManagerParameter p_room("room",    "Room",        "living_room", 63);

    wm.addParameter(&p_backend);
    wm.addParameter(&p_name);
    wm.addParameter(&p_room);

    // autoConnect blocks until connected or portal timeout
    bool connected = wm.autoConnect(PORTAL_AP_NAME);

    if (!connected) {
        Serial.println("[portal] Timed out — rebooting");
        delay(1000);
        ESP.restart();
    }

    // Harvest values entered in the portal
    strlcpy(cfg.backend_url, p_backend.getValue(), sizeof(cfg.backend_url));
    strlcpy(cfg.device_name, p_name.getValue(),    sizeof(cfg.device_name));
    strlcpy(cfg.room,        p_room.getValue(),    sizeof(cfg.room));
    cfg.device_id = 0;  // will be set after registration
}

// ── Reset button ──────────────────────────────────────────────────────────────

void config_check_reset() {
    static unsigned long pressed_at = 0;

    if (digitalRead(RESET_BUTTON_PIN) == LOW) {
        if (pressed_at == 0) pressed_at = millis();
        if (millis() - pressed_at >= RESET_HOLD_MS) {
            Serial.println("[portal] Reset button held — erasing config and rebooting");
            config_erase();
            delay(500);
            ESP.restart();
        }
    } else {
        pressed_at = 0;
    }
}
