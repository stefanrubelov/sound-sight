#pragma once
#include <stdint.h>
#include <string.h>

// Pure-logic mapping: class_name → LED colour + vibration pattern.
// No hardware dependencies — safe to include in native-env unit tests.

struct RGBColor {
    uint8_t r, g, b;
};

enum class VibrationPattern : uint8_t {
    NONE,
    SHORT_PULSE,    // single 200 ms buzz
    DOUBLE_PULSE,   // two 200 ms buzzes with 150 ms gap
    CONTINUOUS,     // 1 s continuous buzz
};

struct AlertProfile {
    RGBColor      color;
    VibrationPattern vib;
    const char*   severity;  // "critical" | "warn" | "info" | "none"
};

inline AlertProfile get_alert_profile(const char* class_name) {
    if (strcmp(class_name, "fire_alarm") == 0)
        return {{255,  30,   0}, VibrationPattern::CONTINUOUS,  "critical"};
    if (strcmp(class_name, "glass_breaking") == 0)
        return {{255,   0,   0}, VibrationPattern::CONTINUOUS,  "critical"};
    if (strcmp(class_name, "baby_crying") == 0)
        return {{255, 165,   0}, VibrationPattern::DOUBLE_PULSE,"warn"};
    if (strcmp(class_name, "doorbell") == 0)
        return {{  0, 120, 255}, VibrationPattern::SHORT_PULSE, "info"};
    if (strcmp(class_name, "dog_barking") == 0)
        return {{160,  32, 240}, VibrationPattern::SHORT_PULSE, "info"};
    if (strcmp(class_name, "timer_beep") == 0)
        return {{  0, 200, 100}, VibrationPattern::SHORT_PULSE, "info"};
    if (strcmp(class_name, "water_running") == 0)
        return {{  0, 180, 255}, VibrationPattern::NONE,        "info"};
    // unknown / below-threshold
    return {{255, 255, 255}, VibrationPattern::NONE, "none"};
}
