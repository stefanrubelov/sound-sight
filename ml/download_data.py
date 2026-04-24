"""
Data download helper for SoundSight.

ESC-50:       Automatically downloadable (MIT-licensed).
UrbanSound8K: Requires free registration at https://urbansounddataset.weebly.com/
              Download manually and extract to ml/data/us8k/

Usage:
    python ml/download_data.py --esc50          # download ESC-50 only
    python ml/download_data.py --esc50 --us8k-path /path/to/us8k  # verify US8K path
"""

import argparse
import logging
import shutil
import urllib.request
import zipfile
from pathlib import Path

log = logging.getLogger(__name__)

ESC50_URL = "https://github.com/karoldvl/ESC-50/archive/master.zip"
DATA_DIR = Path(__file__).parent / "data"


def download_esc50(target_dir: Path = DATA_DIR / "esc50") -> None:
    target_dir.mkdir(parents=True, exist_ok=True)

    if (target_dir / "meta" / "esc50.csv").exists():
        log.info("ESC-50 already downloaded at %s", target_dir)
        return

    zip_path = DATA_DIR / "esc50.zip"
    log.info("Downloading ESC-50 from %s ...", ESC50_URL)
    urllib.request.urlretrieve(ESC50_URL, zip_path)

    log.info("Extracting ...")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(DATA_DIR / "_esc50_tmp")

    extracted = DATA_DIR / "_esc50_tmp" / "ESC-50-master"
    if extracted.exists():
        for item in extracted.iterdir():
            shutil.move(str(item), str(target_dir / item.name))
        shutil.rmtree(DATA_DIR / "_esc50_tmp")

    zip_path.unlink(missing_ok=True)
    log.info("ESC-50 ready at %s", target_dir)


def verify_us8k(us8k_dir: Path = DATA_DIR / "us8k") -> bool:
    meta = us8k_dir / "metadata" / "UrbanSound8K.csv"
    audio = us8k_dir / "audio"
    ok = meta.exists() and audio.is_dir()
    if ok:
        log.info("UrbanSound8K found at %s", us8k_dir)
    else:
        log.warning(
            "UrbanSound8K NOT found at %s\n"
            "  Register and download from: https://urbansounddataset.weebly.com/\n"
            "  Extract so that %s/metadata/UrbanSound8K.csv exists.",
            us8k_dir,
            us8k_dir,
        )
    return ok


def print_custom_instructions() -> None:
    print(
        "\nCustom recordings:\n"
        "  Place 5–10 WAV/MP3 clips per class under ml/data/custom/<class_name>/\n"
        "  Supported classes:\n"
        "    fire_alarm, doorbell, glass_breaking, baby_crying,\n"
        "    dog_barking, timer_beep, water_running, unknown\n"
        "  16 kHz mono preferred (any sample rate is resampled automatically).\n"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--esc50", action="store_true", help="Download ESC-50")
    parser.add_argument("--esc50-dir", default=str(DATA_DIR / "esc50"))
    parser.add_argument(
        "--us8k-path", default=str(DATA_DIR / "us8k"), help="Verify US8K path"
    )
    args = parser.parse_args()

    if args.esc50:
        download_esc50(Path(args.esc50_dir))
    verify_us8k(Path(args.us8k_path))
    print_custom_instructions()
