#include "actuators.h"
#include "config.h"

#include <Arduino.h>
#include <FastLED.h>

static CRGB leds[LED_COUNT];
static unsigned long led_off_at = 0;  // millis() timestamp to clear LED

void actuators_init() {
    FastLED.addLeds<WS2812B, LED_PIN, GRB>(leds, LED_COUNT);
    FastLED.setBrightness(180);
    FastLED.clear(true);

    ledcSetup(VIBRO_CHANNEL, VIBRO_FREQ_HZ, VIBRO_RESOLUTION);
    ledcAttachPin(VIBRO_PIN, VIBRO_CHANNEL);
    ledcWrite(VIBRO_CHANNEL, 0);
}

static void vibrate(VibrationPattern pattern) {
    switch (pattern) {
        case VibrationPattern::SHORT_PULSE:
            ledcWrite(VIBRO_CHANNEL, 200);
            delay(VIBRO_PULSE_MS);
            ledcWrite(VIBRO_CHANNEL, 0);
            break;

        case VibrationPattern::DOUBLE_PULSE:
            ledcWrite(VIBRO_CHANNEL, 200);
            delay(VIBRO_PULSE_MS);
            ledcWrite(VIBRO_CHANNEL, 0);
            delay(150);
            ledcWrite(VIBRO_CHANNEL, 200);
            delay(VIBRO_PULSE_MS);
            ledcWrite(VIBRO_CHANNEL, 0);
            break;

        case VibrationPattern::CONTINUOUS:
            ledcWrite(VIBRO_CHANNEL, 200);
            delay(1000);
            ledcWrite(VIBRO_CHANNEL, 0);
            break;

        case VibrationPattern::NONE:
        default:
            break;
    }
}

void actuators_alert(const AlertProfile& profile) {
    // LED
    leds[0] = CRGB(profile.color.r, profile.color.g, profile.color.b);
    FastLED.show();
    led_off_at = millis() + LED_HOLD_MS;

    // Vibration runs synchronously (short durations, ≤1.6 s)
    vibrate(profile.vib);
}

void actuators_tick() {
    if (led_off_at > 0 && millis() >= led_off_at) {
        actuators_clear();
    }
}

void actuators_clear() {
    FastLED.clear(true);
    ledcWrite(VIBRO_CHANNEL, 0);
    led_off_at = 0;
}
