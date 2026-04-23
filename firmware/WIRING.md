# SoundSight — Hardware Wiring

Wiring for a single SoundSight node built around a **DFRobot FireBeetle 2 ESP32-E** (board ID `DFR0654`). Power comes from USB (5 V). A diagram lives in `firmware/WIRING.svg`.

> **Heads-up for the firmware.** `firmware/src/config.h` currently sets `I2S_SD_PIN = 33`, but **GPIO33 is not brought out on the FireBeetle 2 ESP32-E headers** (neither is GPIO32). This document reassigns it to **GPIO34**. The LED plan also changes because we're using three discrete through-hole LEDs for now rather than a WS2812B — see the _Firmware changes_ section at the bottom.

---

## 1. Bill of materials

### You probably already own

| Qty | Item | Notes |
|---|---|---|
| 1 | FireBeetle 2 ESP32-E board | DFRobot DFR0654 |
| 1 | USB-C cable | Power + flashing |
| 1 | Half-size breadboard (400 tie-point) | Or any solderless breadboard |
| ~15 | Jumper wires (M-M + M-F) | Dupont ribbon is fine |

### Sensor

| Qty | Item | Notes |
|---|---|---|
| 1 | INMP441 I²S MEMS microphone module | 6-pin breakout: VDD, GND, L/R, WS, SCK, SD |

### Visual output (for now)

| Qty | Item | Notes |
|---|---|---|
| 1 | 5 mm LED, red | Fire alarm / critical |
| 1 | 5 mm LED, yellow | Timer / caution |
| 1 | 5 mm LED, green | General / info |
| 3 | 220 Ω resistor | Series resistor, one per LED, 3.3 V drive → ~8 mA |

### Haptic output

| Qty | Item | Notes |
|---|---|---|
| 1 | Coin ERM vibration motor (3 V) | ~70–100 mA, too much for direct GPIO |
| 1 | N-channel logic-level MOSFET | e.g. 2N7000, AO3400, or IRLML2502 |
| 1 | 10 kΩ resistor | Gate pull-down (keeps motor off at boot) |
| 1 | 1N5819 Schottky diode (or 1N4007) | Flyback diode across the motor |
| 1 | 220 Ω resistor _(optional)_ | Gate series resistor, limits inrush |

### Optional / for later

| Qty | Item | Notes |
|---|---|---|
| 1 | WS2812B strip (8–16 px) | Upgrade path — keeps FastLED code useful |
| 1 | 330 Ω resistor | Series on strip data line |
| 1 | 470–1000 µF / 10 V electrolytic cap | Across 5 V and GND near the strip |
| 1 | 128×64 SSD1306 OLED (I²C) | SDA=GPIO21, SCL=GPIO22 — optional, reserved |

---

## 2. Pin map (final)

Everything below is how the firmware will be wired; it supersedes the current `config.h` numbers where noted.

| Function | ESP32 GPIO | FireBeetle silk | Direction | Connects to |
|---|---|---|---|---|
| I²S BCLK (clock)       | **GPIO26** | D3  | OUT | INMP441 **SCK** |
| I²S WS (L/R select)    | **GPIO25** | D2  | OUT | INMP441 **WS** |
| I²S SD (audio data) ⚠  | **GPIO34** | A2  | IN  | INMP441 **SD** |
| LED — Red              | **GPIO17** | D5  | OUT | 220 Ω → LED → GND |
| LED — Yellow           | **GPIO16** | D4  | OUT | 220 Ω → LED → GND |
| LED — Green            | **GPIO27** | D6  | OUT | 220 Ω → LED → GND |
| Vibration motor (PWM)  | **GPIO18** | D10 | OUT | MOSFET gate (via 10 kΩ pull-down) |
| Re-enter config button | GPIO0      | A5/BOOT | IN | On-board BOOT button — reuse; long-press after boot |

⚠ `config.h` today uses GPIO33 for the mic data line. **Change it to 34.** GPIO34 is input-only, which is exactly what an I²S _input_ pin needs, and it's freely exposed on the FireBeetle.

Power rails used:

- **3V3** (FireBeetle 3V3 pin) → INMP441 VDD, LED anodes (through resistors)
- **VCC / 5 V** (FireBeetle USB/VCC pin) → vibration motor supply
- **GND** → common ground for mic, motor loop, MOSFET source, and LED cathodes

---

## 3. Wire-by-wire connections

Read this top-to-bottom while you build.

### 3.1 Microphone (INMP441)

| INMP441 pin | Goes to | Wire colour suggestion |
|---|---|---|
| VDD | FireBeetle **3V3** | red |
| GND | FireBeetle **GND** | black |
| L/R | FireBeetle **GND** | black — ties the mic to the **left** channel (matches the I²S driver) |
| WS  | FireBeetle **D2 / GPIO25** | yellow |
| SCK | FireBeetle **D3 / GPIO26** | blue |
| SD  | FireBeetle **A2 / GPIO34** | green |

Notes:
- INMP441 is a **3.3 V** part. Do **not** wire VDD to 5 V.
- L/R low → mic speaks on the left I²S word. The driver in `firmware/src/audio.cpp` configures left-channel mono, so this must stay low.

### 3.2 Three discrete LEDs

Each LED is wired the same way. Anode is the longer leg.

```
[GPIO] ──> [220 Ω] ──> [LED anode]  (LED cathode) ──> GND
```

| LED | GPIO | Resistor | LED anode | LED cathode |
|---|---|---|---|---|
| Red    | D5 / GPIO17 | 220 Ω | after resistor | GND rail |
| Yellow | D4 / GPIO16 | 220 Ω | after resistor | GND rail |
| Green  | D6 / GPIO27 | 220 Ω | after resistor | GND rail |

The GPIO drives high to light the LED. At 3.3 V minus ~2 V forward drop on a 220 Ω resistor, each LED sinks roughly 6–8 mA, well within the ESP32's per-pin limit.

### 3.3 Vibration motor (low-side MOSFET switch)

A motor can't be driven directly from a GPIO — it stalls current spikes past what the pin can sink. Use a small N-channel logic-level MOSFET as a low-side switch.

```
                          (+)
                   +------[Motor]------+
                   |                   |
                +5V (VCC)       Drain of MOSFET
                                       |
              +---- GPIO18 ---[10 kΩ to GND]---+  Gate
                                       |
                                    Source ── GND
                   |                   |
                   +-[Flyback diode]---+
                       cathode to (+), anode to drain
```

Step by step:

1. Motor **(+)** → FireBeetle **VCC / 5 V**.
2. Motor **(−)** → MOSFET **Drain**.
3. MOSFET **Source** → GND rail.
4. MOSFET **Gate** → FireBeetle **D10 / GPIO18**. Add a **10 kΩ pull-down from Gate to GND** so the motor stays off while the ESP32 boots (GPIO18 is floating during reset). Optional 100–220 Ω resistor in series with the gate limits edge current.
5. **Flyback diode** (Schottky 1N5819, or 1N4007 if that's what you have) across the motor: **cathode (banded end) to +5 V**, anode to Drain. This kills the inductive kick when the motor turns off and protects the MOSFET.

Notes:
- Use a **logic-level** MOSFET (gate turns fully on at 3.3 V). Standard 2N7000 works for small coin motors. AO3400 / IRLML2502 are even better.
- `actuators.cpp` already drives GPIO18 with `ledcWrite` PWM at 1 kHz — that's fine for the MOSFET.

### 3.4 Re-enter config portal button

`RESET_BUTTON_PIN = 0` in `config.h` re-uses the on-board **BOOT** button. You don't need to wire anything for this — just long-press BOOT (≥ 3 s) after the board has finished booting, and the firmware will drop into the WiFiManager AP. Don't hold BOOT at power-on unless you want flash-download mode.

---

## 4. Suggested breadboard layout

Single half-size breadboard, FireBeetle mounted with its USB-C edge at one end so the jumper pins are accessible.

```
   +--------------------------------- breadboard ---------------------------------+
   |   ┌──────────────────────┐                                                   |
   |   │                      │   ┌─────────────┐                                 |
   |   │     FireBeetle 2     │   │  INMP441    │                                 |
   |   │     ESP32-E          │   │  (mic mod)  │                                 |
   |   │                      │   └─────────────┘                                 |
   |   └──────────────────────┘                                                   |
   |                                                                              |
   |          [R]─[LED-R]─|                                                       |
   |          [R]─[LED-Y]─|     ← three LEDs in a row, cathodes on GND rail       |
   |          [R]─[LED-G]─|                                                       |
   |                                                                              |
   |      MOSFET ──┬── flyback diode ──┬── motor (+)  (+5V)                       |
   |               └── gate pull-down 10 kΩ → GND                                 |
   +------------------------------------------------------------------------------+
                  GND rail (blue)                        3V3 / 5V rails (red)
```

Keep wiring short around the mic — especially SCK — and run the mic's GND back to the FireBeetle GND directly (star ground) to keep audio quiet.

---

## 5. Power

- **Source:** USB-C to laptop or wall charger.
- **3V3 pin:** used for INMP441 and the LEDs. The FireBeetle's on-board regulator can comfortably supply well over 100 mA — we're drawing maybe 25 mA peak across the three LEDs + the mic's ~1.5 mA.
- **VCC / 5 V:** used for the vibration motor through the MOSFET. Typical coin ERM pulls 70–100 mA; USB's 500 mA budget handles it.
- **Common ground:** every ground on every module — mic GND, LED cathode rail, MOSFET source, motor (−) return through MOSFET, board GND — must be tied to the same GND rail on the breadboard.

When we later add a WS2812B strip >8 pixels, that's when an external 5 V supply becomes mandatory.

---

## 6. Upgrade path to a WS2812B strip

When you get the strip, very little changes:

1. Reassign one GPIO as `LED_DATA_PIN` — **GPIO5 (D9)** is reserved for this. Put a **330 Ω** resistor inline on the data wire, right at the strip.
2. Add a **470–1000 µF** capacitor across the strip's 5 V and GND close to its input.
3. For ≤ 8 pixels, USB 5 V is enough. For anything longer, use an external 5 V supply and _tie its GND to the FireBeetle GND_.
4. Revert the firmware LED code back to FastLED (see next section — keep your original `actuators.cpp` on a branch or in Git history).

---

## 7. Firmware changes this wiring forces

Two small things in the firmware need to catch up with this plan. These are flagged here so you have a single source of truth before editing code.

1. **`firmware/src/config.h`**
   - Change `I2S_SD_PIN` from `33` → `34`.
   - Add discrete-LED pins: `LED_RED_PIN 17`, `LED_YELLOW_PIN 16`, `LED_GREEN_PIN 27`.
   - You can leave `LED_PIN 5` in place as the reserved data pin for the future WS2812B strip.

2. **`firmware/src/actuators.cpp`**
   - Replace the FastLED colour-set block with three `digitalWrite` (or LEDC-PWM if you want fades) calls against `LED_RED_PIN / LED_YELLOW_PIN / LED_GREEN_PIN`.
   - Map the colour-name coming from the backend to which of the three LEDs to light. Suggested mapping (matches §4.2 of `docs/SoundSight_Project_Plan_v2.pdf`):
     - `red`     → red LED (critical: fire alarm, glass breaking)
     - `yellow`  → yellow LED (timer, kettle, oven beep)
     - `green`   → green LED (informational, unknown, low-severity)
     - `blue`    → red + green ON together (doorbell) _or_ leave green on alone until the strip arrives
     - `white`   → all three ON
   - The vibration motor path in `actuators_alert()` is unchanged.

Once the strip arrives, both files revert to roughly their current shape.

---

## 8. Quick build-check order

Wire and test incrementally so a mistake never compounds:

1. Flash blink first — confirm board, USB cable, PlatformIO toolchain.
2. Wire **only the mic**, run the firmware with the new `I2S_SD_PIN 34`. Watch the serial monitor for the RMS log (Phase 2 checklist item `Capture 1-second buffer and log RMS to serial`). Talking near the mic should change the number visibly.
3. Add the **three LEDs**. Temporarily drive each GPIO high in `setup()` to confirm each lights, then wire it into the real alert path.
4. Add the **MOSFET + motor + flyback diode last**. Test with a short `ledcWrite(VIBRO_CHANNEL, 255)` pulse. Listen / feel. Then integrate.
5. Now run an end-to-end test: send a real `POST /api/audio/classify` from the board and watch the right LED come on and the motor buzz.
