#include "actuators.h"
#include "config.h"

#include <Arduino.h>
#include <FastLED.h>

static CRGB leds[LED_COUNT];
static unsigned long led_off_at = 0;  // millis() timestamp to clear LED

void actuators_init() {
    // Blink onboard LED (GPIO2) to confirm firmware is running
    pinMode(2, OUTPUT);
    for (int i = 0; i < 6; i++) { digitalWrite(2, i % 2); delay(100); }

    FastLED.addLeds<WS2812B, LED_PIN, GRB>(leds, LED_COUNT);
    FastLED.setBrightness(180);
    // Startup test: briefly flash white so we can confirm the strip is wired
    fill_solid(leds, LED_COUNT, CRGB(40, 40, 40));
    FastLED.show();
    delay(400);
    FastLED.clear(true);
}

void actuators_alert(const AlertProfile& profile) {
    CRGB color = CRGB(profile.color.r, profile.color.g, profile.color.b);
    Serial.printf("[led] alert r=%d g=%d b=%d pin=%d count=%d\n",
                  profile.color.r, profile.color.g, profile.color.b,
                  LED_PIN, LED_COUNT);
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
