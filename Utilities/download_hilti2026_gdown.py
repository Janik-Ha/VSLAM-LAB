#!/usr/bin/env python3
"""
Download Hilti 2026 challenge data from Google Drive using gdown.

Uses retry logic to handle rate limiting. No OAuth or rclone config required.
Falls back to manual download instructions if automated download fails.

Usage:
    python download_hilti2026_gdown.py -o ./challenge_data
"""

import argparse
import sys
import time
from pathlib import Path

try:
    import gdown
except ImportError:
    print("ERROR: gdown is not installed. Install with: pip install gdown")
    sys.exit(1)

# Folder ID from https://drive.google.com/drive/folders/1BWFIfEL40Nvj-yeyre5O9dOiYCTWatv5
FOLDER_ID = "1BWFIfEL40Nvj-yeyre5O9dOiYCTWatv5"
FOLDER_URL = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
MAX_RETRIES = 5
RETRY_DELAY_MINUTES = 5


def print_manual_instructions(output_dir: Path) -> None:
    print()
    print("=" * 60)
    print("MANUAL DOWNLOAD (if automated download fails)")
    print("=" * 60)
    print()
    print(f"1. Open in browser: {FOLDER_URL}")
    print("2. Sign in to Google if prompted")
    print("3. Select all (Ctrl+A) or download individual sequence folders")
    print("4. Right-click -> Download (or use the download icon)")
    print(f"5. Extract into: {output_dir.absolute()}")
    print()
    print("   Or use Google Drive desktop app to sync the folder.")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download Hilti 2026 challenge data from Google Drive (gdown + retry)"
    )
    parser.add_argument(
        "-o", "--output",
        default="./challenge_data",
        help="Output directory (default: ./challenge_data)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=MAX_RETRIES,
        help=f"Max retry attempts on failure (default: {MAX_RETRIES})",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Hilti 2026 Challenge Data Download (gdown)")
    print("=" * 60)
    print(f"Source: {FOLDER_URL}")
    print(f"Output: {output_dir.absolute()}")
    print()

    for attempt in range(1, args.retries + 1):
        print(f"Attempt {attempt}/{args.retries}...")
        print("-" * 60)
        try:
            gdown.download_folder(
                url=FOLDER_URL,
                output=str(output_dir),
                quiet=False,
                use_cookies=False,
                remaining_ok=True,
                resume=True,
            )
            print("-" * 60)
            print("Download complete!")
            print(f"  Location: {output_dir.absolute()}")
            return 0
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt < args.retries:
                delay_sec = RETRY_DELAY_MINUTES * 60
                print(f"Waiting {RETRY_DELAY_MINUTES} minutes before retry...")
                time.sleep(delay_sec)
            else:
                print("-" * 60)
                print("All retries exhausted.")
                print_manual_instructions(output_dir)
                return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
