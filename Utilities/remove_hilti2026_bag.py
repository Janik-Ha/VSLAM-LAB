#!/usr/bin/env python3
"""
Remove a Hilti 2026 sequence's ROS2 bag from challenge_data to free disk space.

Use after you have run download-sequence and have rgb_0 + csvs in the benchmark.
The extracted data stays; only the raw bag under challenge_data is removed.

Usage:
    python remove_hilti2026_bag.py floor_1_2025-05-05_run_1
    python remove_hilti2026_bag.py floor_1_2025-05-05_run_1 --dry-run
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

# Same path logic as dataset_hilti2026
VSLAM_LAB_DIR = Path(__file__).resolve().parents[1]
HILTI_ROOT = VSLAM_LAB_DIR / "custom_datasets" / "HILTI2026"


def _challenge_data_root() -> Path:
    env = os.environ.get("HILTI_CHALLENGE_DATA")
    if env:
        return Path(env).resolve()
    return HILTI_ROOT / "challenge_data"


def _sequence_to_bag_path(sequence_name: str) -> Path | None:
    """Return path to the sequence's rosbag dir, or None if not found."""
    m = re.match(r"^(floor_[A-Za-z0-9]+)_(\d{4}-\d{2}-\d{2})_run_(\d+)$", sequence_name)
    if not m:
        return None
    floor, date, run = m.groups()
    rel = Path(floor) / date / f"run_{run}" / "rosbag"
    root = _challenge_data_root()
    for prefix in (rel, Path("data") / rel):
        p = root / prefix
        if p.exists():
            return p
    return root / rel


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove a Hilti 2026 sequence bag to free space (extracted data is kept)"
    )
    parser.add_argument("sequence", help="e.g. floor_1_2025-05-05_run_1")
    parser.add_argument("--dry-run", action="store_true", help="Only print path, do not delete")
    args = parser.parse_args()

    bag_path = _sequence_to_bag_path(args.sequence)
    if bag_path is None:
        print("Invalid sequence name.", file=sys.stderr)
        return 1
    if not bag_path.exists():
        print(f"Bag path does not exist: {bag_path}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"Would remove: {bag_path}")
        return 0

    print(f"Removing {bag_path} to free space ...")
    shutil.rmtree(bag_path)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
