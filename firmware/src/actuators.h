#pragma once
#include "event_map.h"

// Initialise WS2812B LED strip.
void actuators_init();

// Light all LEDs with the alert profile colour.
// Alert clears automatically after LED_HOLD_MS (non-blocking via millis()).
void actuators_alert(const AlertProfile& profile);

// Call from loop() to handle timed LED clear.
void actuators_tick();

// Force all LEDs off.
void actuators_clear();
