# Firmware Testing

## Automated (native-env, no hardware needed)

```bash
cd firmware
pio test -e native
```

Tests `event_map.h` — color mapping and vibration pattern selection for all sound classes.

---

## Manual test checklist

Work through these in order after flashing the firmware.

### 1. Toolchain smoke test
- [ ] `pio run -e esp32dev` compiles without errors
- [ ] `pio run -t upload -e esp32dev` flashes successfully
- [ ] `pio device monitor` shows `SoundSight booting...` on serial

### 2. Config portal (first boot)
- [ ] On first boot, ESP32 broadcasts AP `SoundSight-Setup`
- [ ] Connect phone/laptop to that AP
- [ ] Captive portal opens (or navigate to `192.168.4.1`)
- [ ] Enter WiFi credentials + backend URL + device name + room → Save
- [ ] ESP32 reboots, connects to WiFi, prints IP on serial
- [ ] Serial shows `Registered as device_id=N` (backend must be running)

### 3. Reset button
- [ ] Hold GPIO0 (BOOT button) for 3 s → serial shows "Reset button held — erasing config"
- [ ] ESP32 reboots into config portal again

### 4. I2S microphone
- [ ] Serial prints `RMS=X.X` every ~1 s
- [ ] Clap next to mic → RMS value spikes above 200
- [ ] Background silence → RMS stays below 200 (no POST sent)

### 5. HTTP POST + backend response
- [ ] With backend running, clap → serial shows `class=X confidence=Y.YY ok=1`
- [ ] Backend logs show the incoming POST to `/api/audio/classify`
- [ ] WebSocket client (`websocat`) receives the event JSON

### 6. LED (WS2812B)
- [ ] Fire alarm event → LED turns red-orange, stays on for 3 s then off
- [ ] Doorbell event → LED turns blue for 3 s
- [ ] `unknown` class → LED stays off

### 7. Vibration motor
- [ ] Fire alarm → 1 s continuous buzz
- [ ] Doorbell → single short pulse
- [ ] Baby crying → double pulse (two buzzes with gap)
- [ ] `unknown` → no vibration

### 8. Network resilience
- [ ] Kill WiFi mid-session → ESP32 keeps trying, reconnects when WiFi returns
- [ ] Take backend offline → serial shows retry attempts, no crash
- [ ] Restore backend → next capture POSTs successfully

---

## Wiring reference

| Signal        | ESP32 GPIO | Notes                        |
|---------------|-----------|------------------------------|
| I2S SCK       | 26        | INMP441 SCK                  |
| I2S WS        | 25        | INMP441 WS                   |
| I2S SD        | 33        | INMP441 SD                   |
| WS2812B data  | 5         | via 330 Ω series resistor    |
| Vibration PWM | 18        | via transistor / motor driver|
| Reset button  | 0         | BOOT button on devkit        |

Power: INMP441 on 3.3 V. WS2812B and vibration motor on 5 V with shared GND.
