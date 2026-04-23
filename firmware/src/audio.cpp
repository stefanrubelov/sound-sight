#include "audio.h"
#include "config.h"

#include <Arduino.h>
#include <driver/i2s.h>
#include <math.h>

static const i2s_port_t I2S_PORT = I2S_NUM_0;

void audio_init() {
    const i2s_config_t cfg = {
        .mode                 = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate          = SAMPLE_RATE,
        .bits_per_sample      = I2S_BITS_PER_SAMPLE_32BIT,  // INMP441: 24-bit in 32-bit frame
        .channel_format       = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags     = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count        = I2S_DMA_BUF_COUNT,
        .dma_buf_len          = I2S_DMA_BUF_LEN,
        .use_apll             = false,
        .tx_desc_auto_clear   = false,
        .fixed_mclk           = 0,
    };

    const i2s_pin_config_t pins = {
        .bck_io_num   = I2S_SCK_PIN,
        .ws_io_num    = I2S_WS_PIN,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num  = I2S_SD_PIN,
    };

    i2s_driver_install(I2S_PORT, &cfg, 0, nullptr);
    i2s_set_pin(I2S_PORT, &pins);
    i2s_zero_dma_buffer(I2S_PORT);
}

size_t audio_capture(int16_t* buf, size_t max_samples) {
    const size_t target_samples = (SAMPLE_RATE * CAPTURE_MS) / 1000;
    const size_t samples        = (target_samples < max_samples) ? target_samples : max_samples;

    // Read 32-bit frames from DMA
    static int32_t raw[SAMPLE_RATE];  // 1 s at 16 kHz fits in ~64 KB
    size_t bytes_read = 0;
    i2s_read(I2S_PORT, raw, samples * sizeof(int32_t), &bytes_read, portMAX_DELAY);

    size_t frames = bytes_read / sizeof(int32_t);

    // INMP441 data is left-justified in the 32-bit frame; shift right by 8 to get 24-bit,
    // then again by 8 to scale down to 16-bit.
    for (size_t i = 0; i < frames; i++) {
        buf[i] = (int16_t)(raw[i] >> 16);
    }

    return frames * sizeof(int16_t);
}

float audio_rms(const int16_t* buf, size_t samples) {
    if (samples == 0) return 0.0f;
    double sum = 0.0;
    for (size_t i = 0; i < samples; i++) {
        double s = buf[i];
        sum += s * s;
    }
    return (float)sqrt(sum / samples);
}
