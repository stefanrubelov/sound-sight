"""
Demo backup: inject a fake classified event into the backend without real audio.
Usage: python scripts/inject_event.py [--class fire_alarm] [--device-id 1]
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

CLASSES = [
    "fire_alarm",
    "doorbell",
    "glass_breaking",
    "baby_crying",
    "dog_barking",
    "timer_beep",
    "water_running",
]
BACKEND_URL = "http://localhost:8000"


def inject(class_name: str, device_id: int, confidence: float, base_url: str) -> None:
    payload = json.dumps(
        {
            "class_name": class_name,
            "confidence": confidence,
            "device_id": device_id,
            "duration": 1.0,
        }
    ).encode()

    req = urllib.request.Request(
        f"{base_url}/api/dev/inject_event",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(json.dumps(json.loads(resp.read()), indent=2))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject a fake sound event")
    parser.add_argument("--class", dest="class_name", default="doorbell", choices=CLASSES)
    parser.add_argument("--device-id", type=int, default=1)
    parser.add_argument("--confidence", type=float, default=0.92)
    parser.add_argument("--url", default=BACKEND_URL)
    args = parser.parse_args()

    inject(args.class_name, args.device_id, args.confidence, args.url)


if __name__ == "__main__":
    main()
