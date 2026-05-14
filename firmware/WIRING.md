# SoundSight — Hardware Wiring

Wiring for a single SoundSight node built around an **DFRobot FireBeetle 2 ESP32-E (V1.0)**. Power comes from USB (5 V via micro-USB or USB-C, depending on the board revision).

---

## 1. Bill of materials

### Already have

| Qty | Item | Notes |
|---|---|---|
| 1 | DFRobot FireBeetle 2 ESP32-E V1.0 | DFR0654 |
| 2 | Half-size breadboards | Solderless, 400 tie-points each |
| ~15 | Jumper wires (M-M, M-F, F-F) | Dupont ribbon is fine |

### Ordered

| Qty | Item | Notes |
|---|---|---|
| 1 | INMP441 I2S MEMS microphone module | 6-pin breakout: VDD, GND, L/R, WS, SCK, SD |
| 1 | WS2812B LED strip (1 m, 60 LEDs) | Individually addressable, 5 V, IP30 non-waterproof |
| 1 | 330 Ohm resistor | Inline on LED data line to protect first pixel |
| 1 | 1000 uF / 16 V electrolytic capacitor | Across strip 5 V and GND, smooths inrush current |

### Dropped from scope

- ~~Vibration motor~~ — removed to simplify the build
- ~~SSD1306 OLED display~~ — removed to simplify the build

---

## 2. Pin map

These match `firmware/src/config.h` exactly.

| Function | ESP32 GPIO | Direction | Connects to |
|---|---|---|---|
| I2S BCLK (clock) | **GPIO 14** (D6) | OUT | INMP441 **SCK** |
| I2S WS (L/R select) | **GPIO 15** (A4) | OUT | INMP441 **WS** |
| I2S SD (audio data) | **GPIO 34** (A2) | IN | INMP441 **SD** (input-only pin — perfect for I2S data) |
| WS2812B data | **GPIO 16** (D11) | OUT | 330 Ohm resistor -> strip **DIN** |
| Config reset button | **GPIO 0** (D5/BOOT) | IN | On-board BOOT button (hold 3 s after boot) |

Power rails:

- **3.3 V** (ESP32 3V3 pin) -> INMP441 VDD
- **5 V** (ESP32 VIN/5V pin, from USB) -> WS2812B strip 5 V, capacitor (+)
- **GND** -> common ground for mic, strip, capacitor (-)

---

## 3. Wire-by-wire connections

### 3.1 Microphone (INMP441)

| INMP441 pin | Goes to | Wire colour suggestion |
|---|---|---|
| VDD | ESP32 **3.3 V** | red |
| GND | ESP32 **GND** | black |
| L/R | ESP32 **GND** | black — ties mic to **left** channel |
| WS | ESP32 **GPIO 15** | yellow |
| SCK | ESP32 **GPIO 14** | blue |
| SD | ESP32 **GPIO 34 (A2)** | green |

Notes:

- INMP441 is a **3.3 V** part. Do **not** wire VDD to 5 V.
- L/R tied low = left channel. The I2S driver in `audio.cpp` is configured for left-channel mono, so this must stay low.

### 3.2 WS2812B LED strip

```
ESP32 GPIO 16 ---[330 Ohm]---> strip DIN
ESP32 5V (VIN) ----+----------> strip 5V
                   |
              [1000 uF cap]
                   |
ESP32 GND ---------+----------> strip GND
```

Step by step:

1. Solder or clip three jumper wires onto the strip's **input** end (the end where the arrows point *away* from — arrows show data flow direction).
2. Run the **DIN** wire to a breadboard row. Place the **330 Ohm resistor** between that row and the row connected to **GPIO 16**.
3. Run the strip's **5 V** wire to the breadboard's 5 V rail (fed from the ESP32's VIN/5V pin).
4. Run the strip's **GND** wire to the breadboard's GND rail.
5. Place the **1000 uF electrolytic capacitor** across the 5 V and GND rails, close to where the strip connects. **Long leg (+) to 5 V, short leg (-) to GND.** Getting this backwards will damage the capacitor.

The firmware addresses the first 16 LEDs (`LED_COUNT = 16`). At single-colour alerts and 70% brightness, this draws roughly 224 mA — well within USB power budget.

### 3.3 Config reset button

`RESET_BUTTON_PIN = 0` reuses the on-board **BOOT** button. No extra wiring needed. Long-press BOOT (>= 3 s) after the board has finished booting to re-enter the WiFiManager config portal. Do not hold BOOT at power-on — that enters the bootloader flash mode instead.

---

## 4. Breadboard layout

Two breadboards side by side. ESP32 on the first, mic on the second to keep audio wiring short and away from the LED data line.

```
  Breadboard 1                          Breadboard 2
  +----------------------------+        +-------------------+
  |                            |        |                   |
  |   +-----------------+      |        |   +-----------+   |
  |   |   FireBeetle ESP32-E   |      |  wires |   |  INMP441  |   |
  |   |   (straddles     |      | ------>|   |  (mic)    |   |
  |   |    center gap)   |      |        |   +-----------+   |
  |   +-----------------+      |        |                   |
  |                            |        +-------------------+
  |   [330R]---DIN wire to strip
  |   [1000uF cap] on 5V/GND rail
  |                            |
  +----------------------------+

  WS2812B strip (sitting off the breadboard, wires running to it)
```

Tips:

- Keep the mic's SCK and SD wires short. Long clock lines pick up noise.
- Run the mic's GND directly back to the ESP32 GND pin (star ground), not through a long daisy-chain on the breadboard rail.
- The LED strip sits off the breadboard — just run three wires from its input pads to the breadboard.

---

## 5. Power

- **Source:** USB cable to laptop or wall charger (5 V).
- **3.3 V rail:** powers the INMP441 (~1.5 mA). The ESP32's on-board regulator handles this easily.
- **5 V rail:** powers the WS2812B strip. 16 LEDs at single-colour 70% brightness draw roughly 224 mA. The ESP32 itself draws 100-200 mA. Total is well under USB 2.0's 500 mA limit.
- **Common ground:** every module's GND must be tied to the same GND rail — mic, strip, capacitor, and ESP32.

---

## 6. Build-and-test order

Wire and test incrementally so a mistake never compounds:

1. **Flash a blink sketch** — confirm the board, USB cable, and PlatformIO toolchain all work.
2. **Wire only the mic.** Flash the SoundSight firmware. Open Serial Monitor at 115200 baud. You should see `RMS=` values changing when you talk near the mic. If RMS stays at 0, double-check SD/SCK/WS wiring and that L/R is tied to GND.
3. **Add the LED strip** (with resistor and capacitor). Flash again. The LEDs should light up in the alert colour when the backend returns a classification. If nothing happens, verify the strip arrows point away from DIN, and that GPIO 16 matches `LED_PIN` in config.h.
4. **Connect WiFi.** On first boot with no saved credentials, the ESP32 creates a WiFi AP called `SoundSight-Setup`. Connect to it from your phone, enter your WiFi SSID/password and backend URL.
5. **End-to-end test.** Start the FastAPI backend on your laptop. Make a sound near the mic. Watch the serial log for `class=... confidence=...`. Confirm the LED strip lights up with the right colour. Check the web dashboard for the event arriving over WebSocket.
