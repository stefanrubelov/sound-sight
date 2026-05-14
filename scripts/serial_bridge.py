#!/usr/bin/env python3
# NOTE: pio device monitor and this script cannot use the serial port simultaneously.
# Close the bridge before uploading new firmware.

import argparse
import json
import sys
import wave
from pathlib import Path

import requests
import serial

FRAME_MAGIC_TX = (0xAA, 0x55)
FRAME_MAGIC_RX = bytes([0xBB, 0x66])

DEFAULT_UNKNOWN = {
    "class_name": "unknown",
    "confidence": 0.0,
    "led_color": "#000000",
    "vibration": "none",
}


_record_counter = 0


def _save_wav(pcm: bytearray, record_dir: Path) -> None:
    global _record_counter
    _record_counter += 1
    path = record_dir / f"clip_{_record_counter:04d}.wav"
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(16000)
        wf.writeframes(bytes(pcm))
    print(f"[bridge] Saved {path}")


def run_bridge(
    port: str, baud: int, backend: str, device_id: int, record_dir: Path | None = None
) -> None:
    if record_dir:
        record_dir.mkdir(parents=True, exist_ok=True)
        print(f"[bridge] Recording mode: saving clips to {record_dir}/")
    print(f"[bridge] Opening {port} at {baud} baud")
    with serial.Serial(port, baud, timeout=0.1) as ser:
        print(f"[bridge] Connected. Forwarding to {backend}")
        state = "IDLE"
        frame_len = 0
        pcm_buf = bytearray()
        ascii_buf = bytearray()

        while True:
            data = ser.read(256)
            if not data:
                continue

            for b in data:
                if state == "IDLE":
                    if b == FRAME_MAGIC_TX[0]:
                        # Flush any buffered ASCII debug text first
                        _flush_ascii(ascii_buf)
                        ascii_buf.clear()
                        state = "MAGIC_1"
                    else:
                        ascii_buf.append(b)
                        if b == ord("\n"):
                            _flush_ascii(ascii_buf)
                            ascii_buf.clear()

                elif state == "MAGIC_1":
                    if b == FRAME_MAGIC_TX[1]:
                        state = "HEADER_HIGH"
                    elif b == FRAME_MAGIC_TX[0]:
                        state = "MAGIC_1"  # stay, found another 0xAA
                    else:
                        state = "IDLE"

                elif state == "HEADER_HIGH":
                    frame_len = b << 8
                    state = "HEADER_LOW"

                elif state == "HEADER_LOW":
                    frame_len |= b
                    pcm_buf.clear()
                    state = "PAYLOAD"

                elif state == "PAYLOAD":
                    pcm_buf.append(b)
                    if len(pcm_buf) == frame_len:
                        state = "CHECKSUM"

                elif state == "CHECKSUM":
                    expected = 0
                    for byte in pcm_buf:
                        expected ^= byte
                    if b != expected:
                        print(
                            f"[bridge] WARN: checksum mismatch (got {b:#04x}, expected {expected:#04x}), dropping frame"
                        )
                        state = "IDLE"
                    else:
                        if record_dir:
                            _save_wav(pcm_buf, record_dir)
                        response = _classify(pcm_buf, backend, device_id)
                        _send_response(ser, response)
                    state = "IDLE"

    _flush_ascii(ascii_buf)


def _flush_ascii(buf: bytearray) -> None:
    text = buf.decode("utf-8", errors="replace").rstrip()
    if text:
        print(f"[ESP32] {text}")


def _classify(pcm: bytearray, backend: str, device_id: int) -> dict:
    url = f"{backend}/api/audio/classify?device_id={device_id}"
    print(f"[bridge] Sending {len(pcm)} bytes to backend...")
    try:
        resp = requests.post(
            url,
            data=bytes(pcm),
            headers={"Content-Type": "application/octet-stream"},
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()
        # Backend may return vibration_pattern — map to vibration for firmware
        vibration = body.get("vibration") or body.get("vibration_pattern") or "none"
        result = {
            "class_name": body.get("class_name", "unknown"),
            "confidence": float(body.get("confidence", 0.0)),
            "led_color": body.get("led_color", "#000000"),
            "vibration": vibration,
        }
        print(f"[bridge] Classification: {result['class_name']} ({result['confidence']:.2f})")
        return result
    except Exception as exc:
        print(f"[bridge] Backend error: {exc}")
        return DEFAULT_UNKNOWN.copy()


def _send_response(ser: serial.Serial, result: dict) -> None:
    payload = json.dumps(result, separators=(",", ":")).encode() + b"\n"
    ser.write(FRAME_MAGIC_RX + payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="SoundSight USB-serial bridge")
    parser.add_argument("--port", required=True, help="Serial port, e.g. /dev/cu.wchusbserial1130")
    parser.add_argument("--baud", type=int, default=921600)
    parser.add_argument("--backend", default="http://localhost:8000")
    parser.add_argument("--device-id", type=int, default=1)
    parser.add_argument(
        "--record-dir",
        default=None,
        help="If set, save every captured PCM frame as a WAV file here",
    )
    args = parser.parse_args()

    record_dir = Path(args.record_dir) if args.record_dir else None

    try:
        run_bridge(args.port, args.baud, args.backend, args.device_id, record_dir)
    except KeyboardInterrupt:
        print("\n[bridge] Interrupted. Closing port.")
        sys.exit(0)


if __name__ == "__main__":
    main()
