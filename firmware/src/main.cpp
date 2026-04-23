#include <Arduino.h>

#include "actuators.h"
#include "audio.h"
#include "config.h"
#include "config_portal.h"
#include "event_map.h"
#include "network.h"

// ── Globals ───────────────────────────────────────────────────────────────────

static DeviceConfig g_cfg;

// PCM buffer: 1 s at 16 kHz, 16-bit = 32 KB
static int16_t g_pcm[SAMPLE_RATE];

// ── setup ─────────────────────────────────────────────────────────────────────

void setup() {
    Serial.begin(115200);
    Serial.println("[main] SoundSight booting...");

    pinMode(RESET_BUTTON_PIN, INPUT_PULLUP);
    actuators_init();

    // Load config from NVS; if missing, launch config portal
    if (!config_load(g_cfg)) {
        Serial.println("[main] No config found — starting portal");
        config_portal_run(g_cfg);
        config_save(g_cfg);
    } else {
        // Still need to connect to WiFi (autoConnect with saved credentials)
        config_portal_run(g_cfg);  // wm.autoConnect returns quickly if already configured
    }

    Serial.printf("[main] Connected. Backend: %s\n", g_cfg.backend_url);

    // Register device on first boot (device_id == 0)
    if (g_cfg.device_id == 0) {
        Serial.println("[main] Registering device...");
        int id = network_register_device(g_cfg.backend_url, g_cfg.device_name, g_cfg.room);
        if (id > 0) {
            g_cfg.device_id = id;
            config_save(g_cfg);
            Serial.printf("[main] Registered as device_id=%d\n", id);
        } else {
            Serial.println("[main] Registration failed — will retry next boot");
        }
    }

    audio_init();
    Serial.println("[main] Ready.");
}

// ── loop ──────────────────────────────────────────────────────────────────────

void loop() {
    config_check_reset();
    actuators_tick();

    // Capture 1 second of audio
    size_t bytes = audio_capture(g_pcm, SAMPLE_RATE);
    if (bytes == 0) {
        Serial.println("[main] audio_capture returned 0 — skipping");
        return;
    }

    float rms = audio_rms(g_pcm, bytes / sizeof(int16_t));
    Serial.printf("[main] RMS=%.1f\n", rms);

    // Skip very quiet frames (silence / background noise)
    if (rms < 200.0f) return;

    // POST to backend
    ClassifyResult result = network_classify(g_cfg.backend_url, g_cfg.device_id, g_pcm, bytes);

    Serial.printf("[main] class=%s confidence=%.2f ok=%d\n",
                  result.class_name, result.confidence, result.ok);

    if (!result.ok) return;

    // Drive actuators based on the response class
    AlertProfile profile = get_alert_profile(result.class_name);
    if (profile.vib != VibrationPattern::NONE ||
        strcmp(profile.severity, "none") != 0) {
        actuators_alert(profile);
    }
}
