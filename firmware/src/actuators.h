#pragma once
#include "event_map.h"

// Initialise LED strip and vibration motor PWM.
void actuators_init();

// Drive the LED and vibration motor according to the alert profile.
// Alert clears automatically after LED_HOLD_MS (non-blocking via millis()).
void actuators_alert(const AlertProfile& profile);

// Call from loop() to handle timed LED fade-out.
void actuators_tick();

// Force everything off.
void actuators_clear();
