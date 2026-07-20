# generate_synthetic_data.py
# ------------------------------------------------------------
# Synthetic dataset generator for skin lesion analysis.
# ------------------------------------------------------------
# This script creates a realistic synthetic dataset for a supervised classification task.
# Features: lesion_count, avg_confidence, location_cluster, skin_type (plus weakly-correlated noise columns).
# Target: routine (basic, advanced, premium).
# Dataset size: 5,000 rows.
# Includes label noise, missing values, outliers, class imbalance, and correlated/independent features.



import os
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
N_SAMPLES = 5_000                     # total rows
SEED = 42                             # reproducibility
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_PATH = OUTPUT_DIR / "synthetic_data.csv"

# Feature ranges (realistic limits)
LESION_COUNT_RANGE = (0, 30)          # integer number of lesions
CONFIDENCE_RANGE = (0.0, 1.0)         # average model confidence
LOCATION_CLUSTERS = list(range(5))    # e.g., 0‑4 representing facial zones
SKIN_TYPES = ["oily", "dry", "normal", "combination", "sensitive"]

# Target classes (routines)
ROUTINES = ["basic", "advanced", "premium"]   # 3‑class problem

# ----------------------------------------------------------------------
# Helper: noisy categorical mapping
# ----------------------------------------------------------------------
def map_to_routine(row: pd.Series) -> str:
    """
    Core deterministic mapping from features → routine.
    The mapping is intentionally **non‑linear** and **overlapping** to
    avoid perfect separability.
    """
    # Base score combines lesion count (more lesions → stronger routine)
    # and avg confidence (lower confidence → stronger routine)
    score = (
        0.4 * row["lesion_count"] / LESION_COUNT_RANGE[1]   # normalised count
        - 0.3 * row["avg_confidence"]                     # lower confidence = higher score
        + 0.1 * (row["location_cluster"] / max(LOCATION_CLUSTERS))  # weak influence
    )

    # Skin‑type bias (some skin types tend to need richer routines)
    skin_bias = {
        "oily": 0.1,
        "dry": 0.15,
        "normal": 0.0,
        "combination": 0.12,
        "sensitive": 0.2,
    }
    score += skin_bias[row["skin_type"]]

    # Map score to routine with overlapping thresholds
    if score < 0.15:
        return "basic"
    elif score < 0.35:
        # 10‑20 % label noise injected later
        return "advanced"
    else:
        return "premium"


# ----------------------------------------------------------------------
# Main generation routine
# ----------------------------------------------------------------------
def main() -> None:
    random.seed(SEED)
    np.random.seed(SEED)

    # --------------------------------------------------------------
    # 1. Generate raw (clean) features
    # --------------------------------------------------------------
    lesion_count = np.random.randint(
        LESION_COUNT_RANGE[0], LESION_COUNT_RANGE[1] + 1, size=N_SAMPLES
    )
    avg_confidence = np.random.beta(a=2, b=5, size=N_SAMPLES)  # skewed low‑confidence
    location_cluster = np.random.choice(LOCATION_CLUSTERS, size=N_SAMPLES)
    skin_type = np.random.choice(SKIN_TYPES, size=N_SAMPLES, p=[0.2, 0.2, 0.2, 0.25, 0.15])

    # Weakly correlated “noise” features
    # – patient_id (just a random identifier, no predictive power)
    # – device_temp (normal distribution, tiny effect on routine)
    patient_id = np.arange(1, N_SAMPLES + 1)
    device_temp = np.random.normal(loc=22.0, scale=2.5, size=N_SAMPLES)

    # Assemble DataFrame
    df = pd.DataFrame(
        {
            "lesion_count": lesion_count,
            "avg_confidence": avg_confidence,
            "location_cluster": location_cluster,
            "skin_type": skin_type,
            "patient_id": patient_id,
            "device_temp": device_temp,
        }
    )

    # --------------------------------------------------------------
    # 2. Derive target routine (deterministic) and inject label noise
    # --------------------------------------------------------------
    df["routine"] = df.apply(map_to_routine, axis=1)

    # Introduce 10‑20 % label noise (flip to a random other class)
    noise_rate = random.uniform(0.10, 0.20)
    n_noisy = int(noise_rate * N_SAMPLES)
    noisy_idx = np.random.choice(df.index, size=n_noisy, replace=False)

    for idx in noisy_idx:
        true_label = df.at[idx, "routine"]
        other_labels = [r for r in ROUTINES if r != true_label]
        df.at[idx, "routine"] = random.choice(other_labels)

    # --------------------------------------------------------------
    # 3. Create class imbalance (e.g., 65 % basic, 25 % advanced, 10 % premium)
    # --------------------------------------------------------------
    # We will down‑sample the over‑represented class (basic) to reach the wanted ratio.
    desired_counts = {
        "basic": int(0.65 * N_SAMPLES),
        "advanced": int(0.25 * N_SAMPLES),
        "premium": N_SAMPLES - int(0.65 * N_SAMPLES) - int(0.25 * N_SAMPLES),
    }

    df_balanced = pd.concat(
        [
            df[df["routine"] == cls].sample(
                n=desired_counts[cls], random_state=SEED, replace=True
            )
            for cls in ROUTINES
        ],
        ignore_index=True,
    )

    # --------------------------------------------------------------
    # 4. Inject missing values (3‑5 % per column, randomly)
    # --------------------------------------------------------------
    miss_rate = random.uniform(0.03, 0.05)
    for col in ["lesion_count", "avg_confidence", "location_cluster", "skin_type"]:
        n_missing = int(miss_rate * N_SAMPLES)
        missing_idx = np.random.choice(df_balanced.index, size=n_missing, replace=False)
        df_balanced.loc[missing_idx, col] = np.nan

    # --------------------------------------------------------------
    # 5. Add outliers (1‑3 % of rows)
    # --------------------------------------------------------------
    outlier_rate = random.uniform(0.01, 0.03)
    n_outliers = int(outlier_rate * N_SAMPLES)
    outlier_idx = np.random.choice(df_balanced.index, size=n_outliers, replace=False)

    # Extreme lesion counts and confidence values
    df_balanced.loc[outlier_idx, "lesion_count"] = np.random.randint(80, 120, size=n_outliers)
    df_balanced.loc[outlier_idx, "avg_confidence"] = np.random.uniform(1.2, 2.0, size=n_outliers)

    # --------------------------------------------------------------
    # 6. Shuffle final table
    # --------------------------------------------------------------
    df_final = df_balanced.sample(frac=1.0, random_state=SEED).reset_index(drop=True)

    # --------------------------------------------------------------
    # 7. Persist to CSV (UTF‑8, no index column)
    # --------------------------------------------------------------
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    # --------------------------------------------------------------
    # 8. Print a quick sanity check
    # --------------------------------------------------------------
    print(f"Synthetic dataset written to: {OUTPUT_PATH}")
    print("\n--- Summary ---")
    print(f"Rows               : {len(df_final)}")
    print(f"Classes distribution:\n{df_final['routine'].value_counts(normalize=True).rename('fraction')}")
    print(f"Missing values per column:\n{df_final.isna().mean().rename('missing_frac')}")
    print(f"Outlier rows (lesion_count > 80): { (df_final['lesion_count'] > 80).sum() }")
    print("\nFirst few rows:")
    print(df_final.head().to_string(index=False))


if __name__ == "__main__":
    main()
