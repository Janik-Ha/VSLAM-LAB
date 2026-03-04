"""
Hilti 2026 (Hilti-Trimble SLAM Challenge) dataset adapter for VSLAM-LAB.
Downloads from Google Drive via Hilti scripts, extracts from ROS2 bags using rosbags.
"""

import csv
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from Datasets.DatasetVSLAMLab import DatasetVSLAMLab
from path_constants import VSLAM_LAB_DIR

SCRIPT_LABEL = f"\033[95m[{os.path.basename(__file__)}]\033[0m "

HILTI_ROOT = VSLAM_LAB_DIR / "custom_datasets" / "HILTI2026"
EXTRACT_SCRIPT = VSLAM_LAB_DIR / "Datasets" / "extra-files" / "extract_ros2bag_frames.py"


def _parse_sequence_to_path(sequence_name: str) -> Path:
    """Parse floor_X_YYYY-MM-DD_run_Z -> floor_X/YYYY-MM-DD/run_Z/rosbag/"""
    match = re.match(r"^(floor_[A-Za-z0-9]+)_(\d{4}-\d{2}-\d{2})_run_(\d+)$", sequence_name)
    if not match:
        raise ValueError(f"Invalid Hilti 2026 sequence name: {sequence_name}")
    floor, date, run = match.groups()
    return Path(floor) / date / f"run_{run}" / "rosbag"


class HILTI2026_dataset(DatasetVSLAMLab):
    """Hilti 2026 dataset adapter for VSLAM-LAB."""

    def __init__(self, benchmark_path):
        super().__init__("hilti2026", benchmark_path)
        self.sequence_nicknames = [s.replace("_", " ") for s in self.sequence_names]

    def _get_bag_path(self, sequence_name: str) -> Path:
        rel_path = _parse_sequence_to_path(sequence_name)
        for prefix in ("challenge_data", "challenge_data/data"):
            p = HILTI_ROOT / prefix / rel_path
            if p.exists():
                return p
        return HILTI_ROOT / "challenge_data" / rel_path

    def _ensure_challenge_data(self) -> None:
        """Run Hilti download script if challenge_data does not exist."""
        challenge_data = HILTI_ROOT / "challenge_data"
        if challenge_data.exists():
            return
        download_script = HILTI_ROOT / "challenge_tools_ros" / "download_data" / "download_drive.py"
        if not download_script.exists():
            raise FileNotFoundError(
                f"Hilti download script not found: {download_script}\n"
                "Ensure custom_datasets/HILTI2026 is cloned (e.g. via Utilities/setup_hilti2026.sh)"
            )
        print(f"{SCRIPT_LABEL}Running Hilti download script (this may take a while)...")
        subprocess.run(
            ["python", str(download_script), "-o", str(challenge_data)],
            cwd=str(HILTI_ROOT),
            check=True,
        )

    def download_sequence_data(self, sequence_name: str) -> None:
        self._ensure_challenge_data()
        bag_path = self._get_bag_path(sequence_name)
        if not bag_path.exists():
            raise FileNotFoundError(
                f"ROS2 bag not found: {bag_path}\n"
                f"Sequence {sequence_name} may not be in the downloaded challenge_data."
            )
        sequence_path = self.dataset_path / sequence_name
        sequence_path.mkdir(parents=True, exist_ok=True)

    def create_rgb_folder(self, sequence_name: str) -> None:
        sequence_path = self.dataset_path / sequence_name
        rgb_0_path = sequence_path / "rgb_0"
        if rgb_0_path.exists() and any(rgb_0_path.glob("*.png")):
            return

        bag_path = self._get_bag_path(sequence_name)

        print(f"{SCRIPT_LABEL}Extracting images from {bag_path} -> {rgb_0_path}")
        subprocess.run(
            [
                "python",
                str(EXTRACT_SCRIPT),
                "--bag",
                str(bag_path),
                "--out",
                str(rgb_0_path),
                "--topic",
                "/cam0/image_raw/compressed",
            ],
            check=True,
        )

    def create_rgb_csv(self, sequence_name: str) -> None:
        sequence_path = self.dataset_path / sequence_name
        rgb_csv = sequence_path / "rgb.csv"
        if rgb_csv.exists():
            return

        rgb_0_path = sequence_path / "rgb_0"
        rgb_txt = sequence_path / "rgb.txt"

        if rgb_txt.exists():
            entries = []
            with open(rgb_txt, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        ts_sec, path = parts
                        entries.append((float(ts_sec), path))
            entries.sort(key=lambda x: x[0])
        else:
            rgb_files = sorted(
                f for f in rgb_0_path.iterdir() if f.suffix.lower() in (".png", ".jpg", ".jpeg")
            )
            entries = []
            for f in rgb_files:
                name = f.stem
                try:
                    ts_ns = int(name)
                    ts_sec = ts_ns / 1e9
                except ValueError:
                    continue
                entries.append((ts_sec, f"rgb_0/{f.name}"))

        tmp = rgb_csv.with_suffix(".csv.tmp")
        with open(tmp, "w", newline="", encoding="utf-8") as fout:
            w = csv.writer(fout)
            w.writerow(["ts_rgb_0 (ns)", "path_rgb_0"])
            for ts_sec, path in entries:
                if not path.startswith("rgb_0/"):
                    path = f"rgb_0/{path.split('/')[-1]}"
                ts_ns = int(ts_sec * 1e9)
                w.writerow([ts_ns, path])
        tmp.replace(rgb_csv)

    def create_calibration_yaml(self, sequence_name: str) -> None:
        sequence_path = self.dataset_path / sequence_name
        calibration_yaml = sequence_path / "calibration.yaml"
        if calibration_yaml.exists():
            return

        cal_file = HILTI_ROOT / "config" / "hilti_openvins" / "kalibr_imucam_chain.yaml"
        with open(cal_file, "r") as f:
            cal = yaml.safe_load(f)

        cam0 = cal["cam0"]
        fx, fy, cx, cy = cam0["intrinsics"]
        k1, k2, k3, k4 = cam0["distortion_coeffs"]

        rgb0: dict[str, Any] = {
            "cam_name": "rgb_0",
            "cam_type": "rgb",
            "cam_model": "pinhole",
            "distortion_type": "equid4",
            "distortion_coefficients": [k1, k2, k3, k4],
            "focal_length": [float(fx), float(fy)],
            "principal_point": [float(cx), float(cy)],
            "fps": float(self.rgb_hz),
            "T_BS": np.eye(4),
        }
        self.write_calibration_yaml(sequence_name=sequence_name, rgb=[rgb0])

    def create_groundtruth_csv(self, sequence_name: str) -> None:
        sequence_path = self.dataset_path / sequence_name
        groundtruth_csv = sequence_path / "groundtruth.csv"
        if groundtruth_csv.exists():
            return

        gt_txt = HILTI_ROOT / "groundtruth" / f"{sequence_name}.txt"
        if not gt_txt.exists():
            return

        tmp = groundtruth_csv.with_suffix(".csv.tmp")
        with open(gt_txt, "r", encoding="utf-8") as fin, open(
            tmp, "w", newline="", encoding="utf-8"
        ) as fout:
            w = csv.writer(fout)
            w.writerow(["ts (ns)", "tx (m)", "ty (m)", "tz (m)", "qx", "qy", "qz", "qw"])
            for line in fin:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                parts = s.split()
                ts_ns = int(float(parts[0]) * 1e9)
                w.writerow([ts_ns] + parts[1:])
        tmp.replace(groundtruth_csv)

    def remove_unused_files(self, sequence_name: str) -> None:
        sequence_path = self.dataset_path / sequence_name
        rgb_txt = sequence_path / "rgb.txt"
        if rgb_txt.exists():
            rgb_txt.unlink(missing_ok=True)
