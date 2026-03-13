#!/usr/bin/env python3
"""
Print a performance comparison table from Hilti 2026 benchmark results.
Reads ate.csv from each experiment and prints ATE RMSE (m) per method per sequence.

Usage:
    python Utilities/print_hilti2026_benchmark_table.py configs/exp_hilti2026_bench.yaml
"""

import os
import sys
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
VSLAM_LAB_EVALUATION_FOLDER = "vslamlab_evaluation"
ATE_CSV = "ate.csv"


def load_experiments(exp_yaml: Path) -> dict:
    with open(exp_yaml, "r") as f:
        data = yaml.safe_load(f)
    return data


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python print_hilti2026_benchmark_table.py <exp_yaml>", file=sys.stderr)
        return 1

    exp_yaml = Path(sys.argv[1])
    if not exp_yaml.is_absolute():
        exp_yaml = REPO_ROOT / exp_yaml
    if not exp_yaml.exists():
        print(f"Not found: {exp_yaml}", file=sys.stderr)
        return 1

    # Evaluation root (same as vslamlab: VSLAMLAB_EVALUATION)
    eval_root = REPO_ROOT / "VSLAM-LAB-Evaluation"
    if not eval_root.exists():
        print(f"Evaluation folder not found: {eval_root}", file=sys.stderr)
        return 1

    experiments = load_experiments(exp_yaml)
    # Get sequences from the config referenced by the first experiment
    first_exp = next(iter(experiments.values()))
    config_ref = first_exp["Config"]
    config_path = (Path(config_ref) if Path(config_ref).is_absolute() else REPO_ROOT / "configs" / Path(config_ref).name)
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    dataset_name = "hilti2026"
    sequences = config.get(dataset_name, [])
    dataset_upper = dataset_name.upper()

    # Collect RMSE per (exp_name, sequence)
    rows = []
    for exp_name in experiments:
        exp_folder = eval_root / exp_name
        if not exp_folder.exists():
            rows.append((exp_name, None, None, "no results"))
            continue
        for seq in sequences:
            ate_path = exp_folder / dataset_upper / seq / VSLAM_LAB_EVALUATION_FOLDER / ATE_CSV
            if not ate_path.exists():
                rows.append((exp_name, seq, None, "missing"))
                continue
            try:
                df = pd.read_csv(ate_path)
                if "rmse" not in df.columns or df.empty:
                    rows.append((exp_name, seq, None, "no rmse"))
                    continue
                rmse = df["rmse"].median()
                rows.append((exp_name, seq, rmse, None))
            except Exception as e:
                rows.append((exp_name, seq, None, str(e)))

    # Build table: methods x sequences
    method_names = [e.replace("exp_hilti2026_bench_", "") for e in experiments]
    seq_short = [seq.replace("_2025-", "_").replace("floor_", "f") for seq in sequences]

    print()
    print("ATE RMSE (m) – lower is better")
    print("-" * 60)
    if len(sequences) == 1:
        header = f"{'Method':<18} | {seq_short[0]:<14}"
    else:
        header = f"{'Method':<18} | " + " | ".join(f"{s:<14}" for s in seq_short) + f" | {'Mean':<8}"
    print(header)
    print("-" * 60)

    for i, exp_name in enumerate(experiments):
        method = method_names[i]
        values = []
        for seq in sequences:
            v = None
            for (e, s, rmse, err) in rows:
                if e == exp_name and s == seq:
                    v = rmse if err is None else err
                    break
            values.append(v)
        parts = [f"{v:.4f}" if isinstance(v, (int, float)) else str(v) for v in values]
        if len(sequences) > 1 and all(isinstance(v, (int, float)) for v in values):
            mean = sum(values) / len(values)
            parts.append(f"{mean:.4f}")
        row_str = f"{method:<18} | " + " | ".join(f"{p:<14}" for p in parts)
        print(row_str)

    print("-" * 60)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
