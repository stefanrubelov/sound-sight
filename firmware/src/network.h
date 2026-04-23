#pragma once
#include <stddef.h>
#include <stdint.h>

// Result from a classify call.
struct ClassifyResult {
    char  class_name[32];
    float confidence;
    char  led_color[16];     // hex string e.g. "#FF1E00"
    char  vibration[16];     // "none" | "short" | "double" | "continuous"
    bool  ok;                // false if request failed
};

// Send raw PCM bytes to POST /api/audio/classify.
// backend_url: e.g. "http://192.168.1.100:8000"
// device_id:   registered device ID (0 = not yet registered)
ClassifyResult network_classify(const char* backend_url,
                                int         device_id,
                                const void* pcm_bytes,
                                size_t      byte_count);

// Register this device on first boot.
// Returns assigned device_id (> 0) or -1 on failure.
int network_register_device(const char* backend_url,
                            const char* device_name,
                            const char* room);
