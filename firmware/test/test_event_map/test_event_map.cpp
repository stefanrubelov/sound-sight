#include <unity.h>
#include "../../src/event_map.h"

void setUp() {}
void tearDown() {}

void test_fire_alarm_is_critical() {
    AlertProfile p = get_alert_profile("fire_alarm");
    TEST_ASSERT_EQUAL_STRING("critical", p.severity);
    TEST_ASSERT_EQUAL(VibrationPattern::CONTINUOUS, p.vib);
    TEST_ASSERT_EQUAL_UINT8(255, p.color.r);
}

void test_doorbell_is_info() {
    AlertProfile p = get_alert_profile("doorbell");
    TEST_ASSERT_EQUAL_STRING("info", p.severity);
    TEST_ASSERT_EQUAL(VibrationPattern::SHORT_PULSE, p.vib);
    TEST_ASSERT_EQUAL_UINT8(0, p.color.r);   // blue-ish, no red
}

void test_glass_breaking_is_critical() {
    AlertProfile p = get_alert_profile("glass_breaking");
    TEST_ASSERT_EQUAL_STRING("critical", p.severity);
    TEST_ASSERT_EQUAL(VibrationPattern::CONTINUOUS, p.vib);
}

void test_baby_crying_is_warn_double_pulse() {
    AlertProfile p = get_alert_profile("baby_crying");
    TEST_ASSERT_EQUAL_STRING("warn", p.severity);
    TEST_ASSERT_EQUAL(VibrationPattern::DOUBLE_PULSE, p.vib);
}

void test_unknown_is_none() {
    AlertProfile p = get_alert_profile("unknown");
    TEST_ASSERT_EQUAL_STRING("none", p.severity);
    TEST_ASSERT_EQUAL(VibrationPattern::NONE, p.vib);
}

void test_water_running_no_vibration() {
    AlertProfile p = get_alert_profile("water_running");
    TEST_ASSERT_EQUAL(VibrationPattern::NONE, p.vib);
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_fire_alarm_is_critical);
    RUN_TEST(test_doorbell_is_info);
    RUN_TEST(test_glass_breaking_is_critical);
    RUN_TEST(test_baby_crying_is_warn_double_pulse);
    RUN_TEST(test_unknown_is_none);
    RUN_TEST(test_water_running_no_vibration);
    return UNITY_END();
}
