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
}

void actuators_alert(const AlertProfile& profile) {
    CRGB color = CRGB(profile.color.r, profile.color.g, profile.color.b);
    fill_solid(leds, LED_COUNT, color);
    FastLED.show();
    led_off_at = millis() + LED_HOLD_MS;
}

void actuators_tick() {
    if (led_off_at > 0 && millis() >= led_off_at) {
        actuators_clear();
    }
}

void actuators_clear() {
    FastLED.clear(true);
    led_off_at = 0;
}
