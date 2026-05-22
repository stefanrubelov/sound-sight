# SoundSight — Hardware Wiring

Wiring for a single SoundSight node built around a **DFRobot FireBeetle ESP32-E V1.0**.

---

## 1. Pin map

Matches `firmware/src/config.h` exactly.

| Function | ESP32 GPIO | FireBeetle label | Direction | Connects to |
|---|---|---|---|---|
| I2S BCLK (bit clock) | GPIO 14 | **14/D6** | OUT | INMP441 **SCK** |
| I2S WS (word select) | GPIO 25 | **25/D2** | OUT | INMP441 **WS** |
| I2S SD (audio data) | GPIO 34 | **34/A2** | IN | INMP441 **SD** |
| WS2812B data | GPIO 13 | **13/D7** | OUT | LED strip **DIN** |

---

## 2. Wire-by-wire connections

### 2.1 INMP441 Microphone

| INMP441 pin | Connects to | Note |
|---|---|---|
| VDD | FireBeetle **3V3** | 3.3 V only — never 5 V |
| GND | FireBeetle **GND** | |
| L/R | FireBeetle **3V3** | HIGH = right channel (matches firmware) |
| WS | FireBeetle **25/D2** | |
| SCK | FireBeetle **14/D6** | |
| SD | FireBeetle **34/A2** | GPIO34 is input-only — correct for I2S data |

> **Why right channel?** The INMP441 module has L/R pulled HIGH on its PCB.
> The firmware is configured for `I2S_CHANNEL_FMT_ONLY_RIGHT` to match.

### 2.2 WS2812B LED Strip

| LED strip pin | Connects to | Note |
|---|---|---|
| 5V | External **5V supply** | See note below — do NOT use FireBeetle VCC (3.3 V) |
| GND | Common GND rail | Must share GND with FireBeetle |
| DIN | FireBeetle **13/D7** | Short wire, no resistor needed |

> **Power note:** The FireBeetle VCC pin outputs 3.3 V which is below WS2812B's
> minimum (3.5 V) — LEDs will not light up. The VIN pad on the FireBeetle carries
> 5 V from USB but has no header pin. Options:
> - Solder a wire to the **VIN pad** at the top of the FireBeetle board
> - Power the strip from a separate USB power bank (share GND with FireBeetle)
> - Use a single-cell LiPo via the FireBeetle's JST Li-ion connector

### 2.3 Capacitor

Place a **1000 µF electrolytic capacitor** across the 5V and GND rails close to the
LED strip's input connector. Long leg (+) to 5V, short leg (-) to GND.

---

## 3. Breadboard layout (current)

```
FireBeetle ESP32-E
┌─────────────────────────┐
│ VIN pad (solder/external 5V) ──────────────────┐
│ GND ───────────────────────── GND rail ─────┐  │
│ 3V3 ───────────── INMP441 VDD               │  │
│                   INMP441 L/R ── 3V3        │  │
│ 14/D6 ─────────── INMP441 SCK               │  │
│ 25/D2 ─────────── INMP441 WS                │  │
│ 34/A2 ─────────── INMP441 SD                │  │
│                   INMP441 GND ──────────────┤  │
│                                             │  │
│ 13/D7 ─────────────────────── LED DIN       │  │
│                                LED GND ─────┘  │
│                                LED 5V ─────────┘
└─────────────────────────┘
                          [1000µF cap across 5V/GND at strip input]
```

---

## 4. Alert colours

| Sound class | LED colour | Severity |
|---|---|---|
| fire_alarm | Red-orange `#FF1E00` | critical |
| glass_breaking | Red `#FF0000` | critical |
| baby_crying | Orange `#FFA500` | warn |
| doorbell | Blue `#0078FF` | warn |
| dog_barking | Purple `#A020F0` | warn |
| timer_beep | Green `#00C864` | info |
| water_running | Cyan `#00B4FF` | info |
| unknown | Off | none |
