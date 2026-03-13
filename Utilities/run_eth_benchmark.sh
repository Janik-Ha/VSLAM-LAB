#!/usr/bin/env bash
#
# Run ETH benchmark: vggt-slam, droid-slam, orbslam2, anyfeature, orbslam3, okvis2
# on one sequence (table_3; edit config_eth_bench.yaml to change), then print comparison.
# Also removes previously downloaded Hilti 2026 data and shows a step progress bar.
#
# Usage (from repo root):
#   pixi run -e vslamlab bash Utilities/run_hilti2026_benchmark.sh
#   # or ensure pixi env is active:
#   bash Utilities/run_hilti2026_benchmark.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
EXP_YAML="configs/exp_eth_bench.yaml"
TOTAL_STEPS=6

# Progress: [=====>     ] step/Total
progress_bar() {
  local current=$1
  local total=$2
  local width=20
  local filled=$((width * current / total))
  local empty=$((width - filled))
  printf "\r[\033[92m"
  printf "%${filled}s" | tr ' ' '='
  printf "\033[0m"
  printf "%${empty}s" | tr ' ' ' '
  printf "] %d/%d" "$current" "$total"
}

cd "${REPO_ROOT}"

echo "[run_eth_benchmark] Experiment: ${EXP_YAML}"
echo ""

# 1) Ensure dataset and resources
step=2
progress_bar "$step" "$TOTAL_STEPS"
echo " Getting experiment resources (download sequences if needed) ..."
pixi run -e vslamlab python vslamlab_gui.py get_experiment_resources "${EXP_YAML}"
echo ""

# 2) Run all SLAM methods
step=3
progress_bar "$step" "$TOTAL_STEPS"
echo " Running experiments ..."
pixi run -e vslamlab python vslamlab_gui.py run_exp "${EXP_YAML}" --overwrite
echo ""

# 3) Evaluate (ATE)
step=4
progress_bar "$step" "$TOTAL_STEPS"
echo " Evaluating trajectories ..."
pixi run -e vslamlab python vslamlab_gui.py evaluate_exp "${EXP_YAML}" --overwrite
echo ""

# 4) Compare (figures)
step=5
progress_bar "$step" "$TOTAL_STEPS"
echo " Generating comparison figures ..."
pixi run -e vslamlab python vslamlab_gui.py compare_exp "${EXP_YAML}"
echo ""

# 5) Print performance table
step=6
progress_bar "$step" "$TOTAL_STEPS"
echo " Performance summary"
echo ""
pixi run -e vslamlab python "${SCRIPT_DIR}/print_benchmark_table.py" "${EXP_YAML}"

echo ""
echo "[run_eth_benchmark] Done. Comparison figures: VSLAM-LAB-Evaluation/comp_exp_eth_bench/figures/"
