#!/usr/bin/env python3
"""
Report how many Hilti 2026 sequences are present and how many are left to download.

Uses HILTI_CHALLENGE_DATA if set, else custom_datasets/HILTI2026/challenge_data.

Usage:
    python Utilities/check_hilti2026_status.py
"""

import os
import re
import sys
from pathlib import Path

VSLAM_LAB_DIR = Path(__file__).resolve().parents[1]
HILTI_ROOT = VSLAM_LAB_DIR / "custom_datasets" / "HILTI2026"

EXPECTED_SEQUENCES = [
    "floor_1_2025-05-05_run_1",
    "floor_2_2025-05-05_run_1",
    "floor_2_2025-10-28_run_1",
    "floor_2_2025-10-28_run_2",
    "floor_UG1_2025-10-16_run_1",
]


def challenge_data_root() -> Path:
    env = os.environ.get("HILTI_CHALLENGE_DATA")
    if env:
        return Path(env).resolve()
    return HILTI_ROOT / "challenge_data"


def sequence_bag_exists(root: Path, sequence_name: str) -> bool:
    m = re.match(r"^(floor_[A-Za-z0-9]+)_(\d{4}-\d{2}-\d{2})_run_(\d+)$", sequence_name)
    if not m:
        return False
    floor, date, run = m.groups()
    rel = Path(floor) / date / f"run_{run}" / "rosbag"
    for prefix in (rel, Path("data") / rel):
        if (root / prefix).exists():
            return True
    return False


def main() -> int:
    root = challenge_data_root()
    if not root.exists():
        print(f"Challenge data root does not exist: {root}")
        print("Nothing downloaded yet. Run: pixi run setup-hilti2026")
        return 1

    present = []
    missing = []
    for seq in EXPECTED_SEQUENCES:
        if sequence_bag_exists(root, seq):
            present.append(seq)
        else:
            missing.append(seq)

    n = len(EXPECTED_SEQUENCES)
    print(f"Hilti 2026 challenge data: {root}")
    print(f"Sequences: {len(present)} of {n} present, {len(missing)} left to download")
    if present:
        print("  Present:", ", ".join(present))
    if missing:
        print("  Missing:", ", ".join(missing))
    return 0 if len(missing) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
