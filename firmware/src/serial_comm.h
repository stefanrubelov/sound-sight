#pragma once
#include <stddef.h>
#include <stdint.h>

struct ClassifyResult {
    char  class_name[32];
    float confidence;
    char  led_color[16];
    char  vibration[16];
    bool  ok;                // false if timeout or parse error
};

// Send a framed PCM buffer over Serial and wait for the bridge's JSON response.
ClassifyResult serial_classify(const void* pcm_bytes, size_t byte_count);
