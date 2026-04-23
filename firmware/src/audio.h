#pragma once
#include <stddef.h>
#include <stdint.h>

// Initialise I2S driver for the INMP441 microphone.
void audio_init();

// Capture CAPTURE_MS of audio.
// Writes 16-bit PCM samples into buf (caller owns the buffer).
// Returns number of bytes actually written, or 0 on error.
size_t audio_capture(int16_t* buf, size_t max_samples);

// Compute RMS of a 16-bit PCM buffer (useful for silence detection / serial logging).
float audio_rms(const int16_t* buf, size_t samples);
