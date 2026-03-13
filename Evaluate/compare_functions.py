import os
import warnings

import matplotlib.pyplot as plt
import pandas as pd
import yaml

from Evaluate import plot_functions
from Datasets.get_dataset import get_dataset
from path_constants import VSLAM_LAB_EVALUATION_FOLDER
from utilities import find_common_sequences, read_csv

SCRIPT_LABEL = "[compare_functions.py] "
VSLAM_LAB_ACCURACY_CSV = 'ate.csv'


def _normalize_accuracy_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure accuracy DataFrame has expected columns (evo may use ape_rmse or transposed table)."""
    if df is None or df.empty:
        return df
    # Evo_res table may be transposed: rows = metrics (rmse, mean, ...), cols = trajectory names
    if df.shape[0] <= 10 and df.shape[1] > 1:
        first_vals = df.iloc[:, 0].astype(str).str.strip().str.lower()
        metric_like = first_vals.isin(('rmse', 'ape_rmse', 'mean', 'median', 'std', 'min', 'max', 'sse'))
        if metric_like.sum() >= 2:  # at least 2 rows look like metric names
            df = df.set_index(df.columns[0]).T.reset_index()
            df = df.rename(columns={df.columns[0]: 'traj_name'})
    # Map evo/table output to expected column name for RMSE
    for candidate in ('rmse', 'ape_rmse', 'ATE (m)', 'ape_mean'):
        if candidate in df.columns and 'rmse' not in df.columns:
            df = df.rename(columns={candidate: 'rmse'})
            break
    if 'rmse' not in df.columns:
        for c in df.columns:
            if c in ('traj_name', 'name'):
                continue
            try:
                pd.to_numeric(df[c], errors='raise')
                df = df.rename(columns={c: 'rmse'})
                break
            except (TypeError, ValueError):
                continue
    return df


def full_comparison(experiments, VSLAMLAB_BENCHMARK, COMPARISONS_YAML_DEFAULT, comparison_path):
    figures_path = os.path.join(comparison_path, "figures")

    with open(COMPARISONS_YAML_DEFAULT, 'r') as file:
        comparisons = yaml.safe_load(file)

    dataset_sequences, dataset_nicknames, dataset_rgbHz, exp_names, sequence_nicknames = get_experiments(experiments)
    accuracies = get_accuracies(experiments, dataset_sequences)

    # Comparisons switch
    def switch_comparison(comparison_):
        switcher = {
            'accuracy_boxplot': lambda: plot_functions.boxplot_exp_seq(accuracies, dataset_sequences,
                                                                       'rmse', figures_path, experiments),
            'accuracy_boxplot_shared_scale': lambda: plot_functions.boxplot_exp_seq(accuracies, dataset_sequences,
                                                                       'rmse', figures_path, experiments, shared_scale=True),
            'cumulated_error': lambda: plot_functions.plot_cum_error(accuracies, dataset_sequences, exp_names,
                                                                     dataset_nicknames, 'rmse', figures_path, experiments),
            'accuracy_radar': lambda: plot_functions.radar_seq(accuracies, dataset_sequences, exp_names,
                                                               dataset_nicknames, 'rmse', figures_path, experiments),
            'trajectories': lambda: plot_functions.plot_trajectories(dataset_sequences, exp_names, dataset_nicknames,
                                                                     experiments, accuracies, figures_path),
            'image_canvas': lambda: plot_functions.create_and_show_canvas(dataset_sequences, VSLAMLAB_BENCHMARK, figures_path),
            'num_tracked_frames': lambda: plot_functions.num_tracked_frames(accuracies, dataset_sequences, figures_path, experiments),
            'running_time': lambda: plot_functions.running_time(figures_path, experiments, sequence_nicknames),
            'memory': lambda: plot_functions.plot_memory(figures_path, experiments, sequence_nicknames),
        }

        func = switcher.get(comparison_, lambda: "Invalid case")
        return func()

    # Suppress numpy "Mean of empty slice" / "invalid value in scalar divide" from boxplot on empty/small data
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Mean of empty slice", category=RuntimeWarning)
        warnings.filterwarnings("ignore", message="invalid value encountered in scalar divide", category=RuntimeWarning)
        for comparison in comparisons:
            if comparisons[comparison]:
                switch_comparison(comparison)

    plt.show()


def get_experiments(experiments):
    """
    ------------ Description:
    This function processes a dictionary of experiments to extract and compile common sequences across all experiments,
    as well as relevant metadata such as dataset nicknames, RGB frame rates, experiment names, and folders. It ensures
    that sequences common to all experiments are identified and organizes the data in a structured format for further
    analysis.

    ------------ Parameters:
    experiments : dict
        experiments[exp_name] = experiment

    ------------ Returns:
    dataset_sequences : dict
        dataset_sequences[dataset_name] = list{sequence_names}
    dataset_nicknames : dict
        dataset_nicknames[dataset_name] = list{sequence_nicknames}
    dataset_rgbHz : dict
        dataset_rgbHz[dataset_name] = sequence_rgbHz
    exp_names : list
        exp_names = list{exp_names}
    exp_folders : list
        exp_folders = list{exp_folders}
"""

    # Find sequences common to all experiments
    dataset_sequences = find_common_sequences(experiments)

    # Lists with the experiment names and folders
    exp_names = []
    exp_folders = []
    for exp_name, exp in experiments.items():
        exp_names.append(exp_name)
        exp_folders.append(exp.folder)

    dataset_nicknames = {}
    sequence_nicknames = {}
    dataset_rgbHz = {}
    for dataset_name, sequence_names in dataset_sequences.items():
        dataset = get_dataset(dataset_name, "-")
        dataset_nicknames[dataset_name] = []
        dataset_rgbHz[dataset_name] = dataset.rgb_hz
        for sequence_name in sequence_names:
            sequences_nickname = dataset.get_sequence_nickname(sequence_name)
            sequence_nicknames[sequence_name] = sequences_nickname
            dataset_nicknames[dataset_name].append(sequences_nickname)

    return dataset_sequences, dataset_nicknames, dataset_rgbHz, exp_names, sequence_nicknames


def get_accuracies(experiments, dataset_sequences):
    """
    ------------ Description:
    Reads accuracy CSV files from a specified folder structure and stores them in a nested dictionary.
    The CSV files are read with space as a delimiter and no header.

    ------------ Parameters:
    experiments : dict
        experiments[exp_name] = experiment
    dataset_sequences : dict
        dataset_sequences[dataset_name] = list{sequence_names}

    ------------ Returns:
    accuracies : dict
        accuracies[dataset_name][sequence_name][exp_name] = pandas.DataFrame()
    """

    accuracies = {}
    for dataset_name, sequence_names in dataset_sequences.items():
        accuracies[dataset_name] = {}
        for sequence_name in sequence_names:
            accuracies[dataset_name][sequence_name] = {}
            for exp_name, exp in experiments.items():
                accuracy_csv_file = os.path.join(exp.folder, dataset_name.upper(), sequence_name,
                                                 os.path.join(VSLAM_LAB_EVALUATION_FOLDER, VSLAM_LAB_ACCURACY_CSV))
                df = read_csv(accuracy_csv_file)
                accuracies[dataset_name][sequence_name][exp_name] = _normalize_accuracy_df(df)

    return accuracies
