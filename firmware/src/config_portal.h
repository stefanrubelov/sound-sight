#pragma once
#include <stdint.h>

struct DeviceConfig {
    char backend_url[128];
    char device_name[64];
    char room[64];
    int  device_id;   // 0 = not yet registered
};

// Load config from NVS into out. Returns true if valid config found.
bool config_load(DeviceConfig& out);

// Save config to NVS.
void config_save(const DeviceConfig& cfg);

// Erase NVS config (forces re-entry of config portal on next boot).
void config_erase();

// Block until WiFi is connected.
// On first boot (or after config_erase), starts AP mode so user can configure.
// Populates cfg.backend_url / device_name / room from the captive portal form.
void config_portal_run(DeviceConfig& cfg);

// Check reset button — call from loop(). Erases config + reboots if held for RESET_HOLD_MS.
void config_check_reset();
