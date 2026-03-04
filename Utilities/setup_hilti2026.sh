#!/usr/bin/env bash

set -euo pipefail

# Resolve repository root (one level up from this Utilities folder)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
REPO_ROOT="$( cd "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd )"

CUSTOM_DATASETS_DIR="${REPO_ROOT}/custom_datasets"
HILTI_DIR="${CUSTOM_DATASETS_DIR}/HILTI2026"
HILTI_REPO_URL="https://github.com/Hilti-Research/hilti-trimble-slam-challenge-2026.git"

echo "[setup_hilti2026] Repository root: ${REPO_ROOT}"

# 1) Ensure custom_datasets folder exists
mkdir -p "${CUSTOM_DATASETS_DIR}"
echo "[setup_hilti2026] Ensured folder: ${CUSTOM_DATASETS_DIR}"

# 2) Clone or update the Hilti 2026 dataset repo
if [ ! -d "${HILTI_DIR}/.git" ]; then
    echo "[setup_hilti2026] Cloning Hilti 2026 dataset into ${HILTI_DIR} ..."
    git clone "${HILTI_REPO_URL}" "${HILTI_DIR}"
else
    echo "[setup_hilti2026] Existing clone found in ${HILTI_DIR}, pulling latest changes ..."
    git -C "${HILTI_DIR}" pull --ff-only
fi

echo "[setup_hilti2026] Hilti 2026 dataset available at: ${HILTI_DIR}"

# 3) Download challenge data (gdown with retry - no rclone/OAuth required)
DOWNLOAD_SCRIPT="${SCRIPT_DIR}/download_hilti2026_gdown.py"
CHALLENGE_DATA="${HILTI_DIR}/challenge_data"

if [ -f "${DOWNLOAD_SCRIPT}" ]; then
    if [ ! -d "${CHALLENGE_DATA}" ] || [ -z "$(ls -A "${CHALLENGE_DATA}" 2>/dev/null)" ]; then
        echo "[setup_hilti2026] Downloading challenge data (gdown, output: ${CHALLENGE_DATA}) ..."
        (python "${DOWNLOAD_SCRIPT}" -o "${CHALLENGE_DATA}") || {
            echo "[setup_hilti2026] WARNING: Automated download failed."
            echo "  Manual: Open https://drive.google.com/drive/folders/1BWFIfEL40Nvj-yeyre5O9dOiYCTWatv5"
            echo "  Download via browser and extract to: ${CHALLENGE_DATA}"
        }
    else
        echo "[setup_hilti2026] challenge_data already exists; skipping download."
    fi
else
    echo "[setup_hilti2026] NOTE: download_hilti2026_gdown.py not found at ${DOWNLOAD_SCRIPT}"
fi

# 4) Verify that all expected sequences exist
EXPECTED_SEQUENCES=(
  "floor_1_2025-05-05_run_1"
  "floor_2_2025-05-05_run_1"
  "floor_2_2025-10-28_run_1"
  "floor_2_2025-10-28_run_2"
  "floor_UG1_2025-10-16_run_1"
)

missing=()

for seq in "${EXPECTED_SEQUENCES[@]}"; do
    if [[ "${seq}" =~ ^(floor_[A-Za-z0-9]+)_([0-9]{4}-[0-9]{2}-[0-9]{2})_run_([0-9]+)$ ]]; then
        floor="${BASH_REMATCH[1]}"
        date="${BASH_REMATCH[2]}"
        run="${BASH_REMATCH[3]}"
    else
        echo "[setup_hilti2026] WARNING: Cannot parse sequence name: ${seq}"
        continue
    fi

    found=0
    for prefix in "challenge_data" "challenge_data/data"; do
        candidate="${HILTI_DIR}/${prefix}/${floor}/${date}/run_${run}/rosbag"
        if [ -d "${candidate}" ]; then
            echo "[setup_hilti2026] OK: found data for ${seq} at ${candidate}"
            found=1
            break
        fi
    done

    if [ "${found}" -eq 0 ]; then
        echo "[setup_hilti2026] MISSING: no data found for ${seq}"
        missing+=("${seq}")
    fi
done

if [ "${#missing[@]}" -ne 0 ]; then
    echo "[setup_hilti2026] Missing data detected, trying to download again via gdown ..."
    if [ -f "${DOWNLOAD_SCRIPT}" ]; then
        (python "${DOWNLOAD_SCRIPT}" -o "${CHALLENGE_DATA}") || {
            echo "[setup_hilti2026] WARNING: Second automated download attempt failed."
        }
    else
        echo "[setup_hilti2026] WARNING: ${DOWNLOAD_SCRIPT} not found, cannot auto-download missing data."
    fi

    # Re-check only sequences that were missing before
    still_missing=()
    for seq in "${missing[@]}"; do
        if [[ "${seq}" =~ ^(floor_[A-Za-z0-9]+)_([0-9]{4}-[0-9]{2}-[0-9]{2})_run_([0-9]+)$ ]]; then
            floor="${BASH_REMATCH[1]}"
            date="${BASH_REMATCH[2]}"
            run="${BASH_REMATCH[3]}"
        else
            echo "[setup_hilti2026] WARNING: Cannot parse sequence name on re-check: ${seq}"
            continue
        fi

        found=0
        for prefix in "challenge_data" "challenge_data/data"; do
            candidate="${HILTI_DIR}/${prefix}/${floor}/${date}/run_${run}/rosbag"
            if [ -d "${candidate}" ]; then
                echo "[setup_hilti2026] OK (after retry): found data for ${seq} at ${candidate}"
                found=1
                break
            fi
        done

        if [ "${found}" -eq 0 ]; then
            still_missing+=("${seq}")
        fi
    done

    if [ "${#still_missing[@]}" -ne 0 ]; then
        echo "[setup_hilti2026] ERROR: Still missing data for the following sequences:"
        for seq in "${still_missing[@]}"; do
            echo "  - ${seq}"
        done
        echo "[setup_hilti2026] Please check your download (or manual extraction) of challenge_data."
        exit 1
    fi
fi

echo "[setup_hilti2026] Done."
echo ""
echo "  To download and prepare a sequence for VSLAM-LAB, run (from repo root):"
echo "    pixi run setup-hilti2026"
echo "    pixi run download-sequence hilti2026 floor_1_2025-05-05_run_1"
echo ""
echo "  Available sequences: floor_1_2025-05-05_run_1, floor_2_2025-05-05_run_1,"
echo "    floor_2_2025-10-28_run_1, floor_2_2025-10-28_run_2, floor_UG1_2025-10-16_run_1"
