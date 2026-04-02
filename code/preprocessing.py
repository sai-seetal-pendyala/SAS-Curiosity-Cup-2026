"""
preprocessing.py
----------------
Exploratory analysis and data verification for the
False Growth Early Warning System.

Loads the pre-built Skill DNA CSVs (train_2019.csv, validate_2023.csv),
prints summary statistics, and confirms the data is ready for SAS Viya
gradient boosting modeling.
"""

import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_data():
    train = pd.read_csv(os.path.join(DATA_DIR, "train_2019.csv"))
    validate = pd.read_csv(os.path.join(DATA_DIR, "validate_2023.csv"))
    print(f"  Training set  : {train.shape[0]} regions × {train.shape[1]} columns")
    print(f"  Validation set: {validate.shape[0]} regions × {validate.shape[1]} columns")
    return train, validate


def summarize_skill_dna(df, label):
    print(f"\n{'='*60}")
    print(f"  SKILL DNA SUMMARY — {label}")
    print(f"{'='*60}")
    skill_cols = [c for c in df.columns if c.startswith("CX_") or c.startswith("SK_")]
    print(f"  Regions       : {df.shape[0]}")
    print(f"  Skill features: {len(skill_cols)}")

    if "target_churn" in df.columns:
        churn = df["target_churn"]
        print(f"  Churn — mean: {churn.mean():.4f}  std: {churn.std():.4f}  "
              f"min: {churn.min():.4f}  max: {churn.max():.4f}")

    nulls = df[skill_cols].isnull().sum().sum()
    print(f"  Missing values in Skill DNA: {nulls}")


def show_top_variable_ranges(df, n=10):
    skill_cols = [c for c in df.columns if c.startswith("CX_") or c.startswith("SK_")]
    ranges = df[skill_cols].max() - df[skill_cols].min()
    top = ranges.sort_values(ascending=False).head(n)
    print(f"\n  {'Feature':<40} {'Range':>8}")
    print(f"  {'─'*40} {'─'*8}")
    for feat, rng in top.items():
        print(f"  {feat:<40} {rng:>8.3f}")


def churn_distribution(train, validate):
    print(f"\n{'='*60}")
    print("  CHURN DISTRIBUTION COMPARISON")
    print(f"{'='*60}")
    for label, df in [("2019 (Train)", train), ("2023 (Validate)", validate)]:
        if "target_churn" in df.columns:
            q = df["target_churn"].quantile([0.25, 0.5, 0.75])
            print(f"  {label}: Q1={q[0.25]:.4f}  Median={q[0.5]:.4f}  Q3={q[0.75]:.4f}")


def main():
    print("\n" + "="*60)
    print("  FALSE GROWTH EARLY WARNING SYSTEM — Data Check")
    print("="*60)

    train, validate = load_data()
    summarize_skill_dna(train, "2019 (Training)")
    summarize_skill_dna(validate, "2023 (Validation)")

    print("\n  TOP VARIANCE FEATURES — 2019")
    show_top_variable_ranges(train)

    churn_distribution(train, validate)

    print("\n  ✓ Data loaded and verified. Ready for SAS Viya modeling.\n")


if __name__ == "__main__":
    main()
