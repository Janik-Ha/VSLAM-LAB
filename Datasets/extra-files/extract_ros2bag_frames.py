#!/usr/bin/env python3
"""
Extract image frames from ROS2 bag files (no ROS2 runtime required).
Uses rosbags + rosbags-image for pure-Python extraction.
"""

import argparse
import os
from pathlib import Path

import cv2
from tqdm import tqdm

try:
    from rosbags.highlevel import AnyReader
    from rosbags.image import message_to_cvimage
except ImportError as e:
    raise ImportError(
        "rosbags and rosbags-image are required. Install with: pip install rosbags rosbags-image"
    ) from e


def main():
    parser = argparse.ArgumentParser(
        description="Extract image frames from ROS2 bag to rgb_0 folder (no ROS2 runtime)"
    )
    parser.add_argument("--bag", required=True, help="Path to ROS2 bag folder")
    parser.add_argument("--out", required=True, help="Output directory (rgb_0)")
    parser.add_argument(
        "--topic",
        default="/cam0/image_raw/compressed",
        help="Image topic (default: /cam0/image_raw/compressed)",
    )
    args = parser.parse_args()

    bag_path = Path(args.bag)
    out_path = Path(args.out)
    topic = args.topic

    if not bag_path.exists():
        raise FileNotFoundError(f"Bag path does not exist: {bag_path}")

    out_path.mkdir(parents=True, exist_ok=True)
    rgb_txt_path = out_path.parent / "rgb.txt"

    connections = None
    with AnyReader([bag_path]) as reader:
        connections = [c for c in reader.connections if c.topic == topic]
        if not connections:
            available = [c.topic for c in reader.connections]
            raise ValueError(
                f"Topic {topic} not found in bag. Available: {available}"
            )

        with open(rgb_txt_path, "w") as f_txt:
            f_txt.write("# timestamp rgb_0/filename\n")
            for connection, timestamp, rawdata in tqdm(
                reader.messages(connections=connections),
                desc=f"Extracting {topic}",
            ):
                try:
                    msg = reader.deserialize(rawdata, connection.msgtype)
                    img = message_to_cvimage(msg, "bgr8")
                except Exception as e:
                    print(f"Warning: failed to decode image at {timestamp}: {e}")
                    continue

                filename = f"{timestamp}.png"
                out_file = out_path / filename
                if not cv2.imwrite(str(out_file), img):
                    print(f"Warning: failed to write {out_file}")
                    continue

                ts_sec = timestamp / 1e9
                f_txt.write(f"{ts_sec:.6f} rgb_0/{filename}\n")

    print(f"Extracted to {out_path}")
    print(f"Wrote {rgb_txt_path}")


if __name__ == "__main__":
    main()
