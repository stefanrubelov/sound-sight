#pragma once
#include "serial_comm.h"  // reuse ClassifyResult
#include <stddef.h>
#include <stdint.h>

// Connect to WiFi. Call once from setup().
void wifi_init();

// POST raw PCM bytes to the backend and return the classification result.
ClassifyResult wifi_classify(const void* pcm_bytes, size_t byte_count);
