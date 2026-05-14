#include <Arduino.h>
#include "config.h"
#include "audio.h"
#include "actuators.h"
#include "event_map.h"
#include "serial_comm.h"

static int16_t g_pcm[SAMPLE_RATE];

void setup() {
    Serial.begin(SERIAL_BAUD);
    Serial.println("[main] SoundSight booting (serial mode)...");
    actuators_init();
    audio_init();
    Serial.println("[main] Ready.");
}

void loop() {
    actuators_tick();

    size_t bytes = audio_capture(g_pcm, SAMPLE_RATE);
    if (bytes == 0) {
        Serial.println("[main] audio_capture returned 0 -- skipping");
        return;
    }

    float rms = audio_rms(g_pcm, bytes / sizeof(int16_t));
    Serial.printf("[main] RMS=%.1f\n", rms);

    if (rms < 200.0f) return;

    ClassifyResult result = serial_classify(g_pcm, bytes);

    Serial.printf("[main] class=%s confidence=%.2f ok=%d\n",
                  result.class_name, result.confidence, result.ok);

    if (!result.ok) return;

    AlertProfile profile = get_alert_profile(result.class_name);
    if (strcmp(profile.severity, "none") != 0) {
        actuators_alert(profile);
    }
}
