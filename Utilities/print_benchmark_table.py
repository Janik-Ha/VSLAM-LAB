#!/usr/bin/env python3
"""
Print a performance comparison table from benchmark results (ETH, Hilti 2026, etc.).
Reads ate.csv from each experiment and prints ATE RMSE (m) per method per sequence.
Infers dataset and method names from exp_yaml and its config.
Uses path_constants so paths match the rest of the codebase.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
import yaml

from path_constants import VSLAMLAB_EVALUATION, VSLAM_LAB_EVALUATION_FOLDER

ATE_CSV = "ate.csv"


def load_experiments(exp_yaml: Path) -> dict:
    with open(exp_yaml, "r") as f:
        data = yaml.safe_load(f)
    return data


def _dataset_from_config(config: dict) -> str:
    """First top-level key in config that maps to a list (sequence list)."""
    for k, v in config.items():
        if k.startswith("#"):
            continue
        if isinstance(v, list):
            return k
    return ""


def _common_prefix(strings: list[str]) -> str:
    if not strings:
        return ""
    prefix = strings[0]
    for s in strings[1:]:
        while not s.startswith(prefix) and prefix:
            prefix = prefix[:-1]
    return prefix


def _rmse_column(df: pd.DataFrame) -> str | None:
    """Return the column name to use for RMSE (evo may use ape_rmse, etc.)."""
    if df is None or df.empty:
        return None
    for candidate in ("rmse", "ape_rmse", "ATE (m)", "ape_mean"):
        if candidate in df.columns:
            return candidate
    for c in df.columns:
        if c in ("traj_name", "name"):
            continue
        try:
            pd.to_numeric(df[c], errors="raise")
            return c
        except (TypeError, ValueError):
            continue
    return None


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python print_benchmark_table.py <exp_yaml>", file=sys.stderr)
        return 1

    exp_yaml = Path(sys.argv[1])
    if not exp_yaml.is_absolute():
        exp_yaml = REPO_ROOT / exp_yaml
    if not exp_yaml.exists():
        print(f"Not found: {exp_yaml}", file=sys.stderr)
        return 1

    eval_root = Path(VSLAMLAB_EVALUATION)
    if not eval_root.exists():
        print(f"Evaluation folder not found: {eval_root}", file=sys.stderr)
        return 1

    experiments = load_experiments(exp_yaml)
    first_exp = next(iter(experiments.values()))
    config_ref = first_exp["Config"]
    config_path = Path(config_ref) if Path(config_ref).is_absolute() else REPO_ROOT / "configs" / Path(config_ref).name
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    dataset_name = _dataset_from_config(config)
    if not dataset_name:
        print("Could not infer dataset from config", file=sys.stderr)
        return 1
    sequences = config.get(dataset_name, [])
    dataset_upper = dataset_name.upper()

    # Method prefix: e.g. exp_eth_bench_ -> vggtslam, droidslam, ...
    exp_names = list(experiments.keys())
    prefix = _common_prefix(exp_names)
    if prefix.endswith("_"):
        method_names = [e[len(prefix):] for e in exp_names]
    else:
        method_names = exp_names

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
                if df.empty:
                    rows.append((exp_name, seq, None, "empty"))
                    continue
                rmse_col = _rmse_column(df)
                if rmse_col is None:
                    rows.append((exp_name, seq, None, "no rmse"))
                    continue
                rmse_val = pd.to_numeric(df[rmse_col], errors="coerce").median()
                if pd.isna(rmse_val):
                    rows.append((exp_name, seq, None, "no rmse"))
                    continue
                rows.append((exp_name, seq, float(rmse_val), None))
            except Exception as e:
                rows.append((exp_name, seq, None, str(e)))

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
    missing_count = sum(1 for _, _, _, err in rows if err == "missing")
    if missing_count == len(rows) and rows:
        first_exp_name = next(iter(experiments.keys()))
        first_seq = sequences[0]
        sample_path = eval_root / first_exp_name / dataset_upper / first_seq / VSLAM_LAB_EVALUATION_FOLDER / ATE_CSV
        print(f"Hint: all ate.csv missing. Expected path example: {sample_path}", file=sys.stderr)
        print("      Run the evaluate step first: pixi run -e vslamlab python vslamlab_gui.py evaluate_exp <exp_yaml> --overwrite", file=sys.stderr)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
