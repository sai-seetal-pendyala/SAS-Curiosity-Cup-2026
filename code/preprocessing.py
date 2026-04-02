#!/usr/bin/env python3
"""
Prepare False Growth Detector datasets locally.

Outputs CSVs that can be uploaded into SAS Model Studio:
  - train_2019.csv
  - validate_2023.csv
  - X_2019.csv
  - Y_2019.csv
  - Y_2023.csv
  - feature_stats.csv
  - top_features.csv
  - prep_manifest.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd


INPUT_FILES = {
    "onet_skills_19": "ONET Skills_2019.xlsx",
    "onet_skills_23": "ONET Skills_2023.xlsx",
    "onet_context_19": "ONET Work Context_2019.xlsx",
    "onet_context_23": "ONET Work Context_2023.xlsx",
    "bls_oews_19": "BLS_OEWS_MSA_2019.xlsx",
    "bls_oews_23": "BLS_OEWS_MSA_2023.xlsx",
    "bls_proj_19": "BLS_Employment Projections_2019.xlsx",
    "bls_proj_23": "BLS_Employment Projections_2023.xlsx",
}


def _load_excel_file(key: str, filepath: Path) -> tuple[str, pd.DataFrame]:
    if "proj" in key:
        df = pd.read_excel(filepath, sheet_name="Table 1.10", skiprows=1)
    else:
        df = pd.read_excel(filepath)
    return key, df


def load_excel_files(data_dir: Path, workers: int) -> dict[str, pd.DataFrame]:
    dfs: dict[str, pd.DataFrame] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for key, filename in INPUT_FILES.items():
            filepath = data_dir / filename
            print(f"Loading {filepath} ...")
            futures.append(executor.submit(_load_excel_file, key, filepath))
        for future in as_completed(futures):
            key, df = future.result()
            dfs[key] = df
            print(f"  -> {key}: {len(df):,} rows, {len(df.columns)} columns")
    return dfs


def clean_feature_name(name: str, prefix: str) -> str:
    clean = "".join(ch for ch in str(name) if ch.isalnum())
    return f"{prefix}_{clean}"


def clean_soc_code(soc: str | float | int) -> str | None:
    if pd.isna(soc):
        return None
    return str(soc).split(".")[0]


def clean_onet_data(df: pd.DataFrame, year: str, scale_filter: str) -> pd.DataFrame:
    prefix = "SK" if scale_filter == "IM" else "CX"
    filtered = df[df["Scale ID"] == scale_filter].copy()
    filtered["soc_code"] = filtered["O*NET-SOC Code"].apply(clean_soc_code)
    filtered["feature_name"] = filtered["Element Name"].apply(
        lambda x: clean_feature_name(x, prefix)
    )
    filtered["score"] = pd.to_numeric(filtered["Data Value"], errors="coerce")
    result = filtered[["soc_code", "feature_name", "score"]].dropna()
    print(
        f"  Cleaned O*NET ({prefix}, {year}): "
        f"{len(result):,} rows, {result['feature_name'].nunique()} features"
    )
    return result


def _normalize_col(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _find_col(columns: list[str], candidates: list[str]) -> str | None:
    normalized = {_normalize_col(c): c for c in columns}
    for cand in candidates:
        key = _normalize_col(cand)
        if key in normalized:
            return normalized[key]
    return None


def _find_col_contains(columns: list[str], must_have: list[str]) -> str | None:
    normalized = {c: _normalize_col(c) for c in columns}
    for col, norm in normalized.items():
        if all(token in norm for token in must_have):
            return col
    return None


def clean_oews_data(df: pd.DataFrame, year: str) -> pd.DataFrame:
    columns = list(df.columns)

    o_group_col = _find_col(columns, ["O_GROUP", "OCC_GROUP", "OCCGRP", "OCC_GROUP"])
    if not o_group_col:
        o_group_col = _find_col_contains(columns, ["group"])

    tot_emp_col = _find_col(columns, ["TOT_EMP", "TOTAL_EMP", "TOTAL_EMPLOYMENT"])
    if not tot_emp_col:
        tot_emp_col = _find_col_contains(columns, ["tot", "emp"])

    occ_code_col = _find_col(columns, ["OCC_CODE", "SOC_CODE", "OCCCODE", "SOCCODE"])
    if not occ_code_col:
        occ_code_col = _find_col_contains(columns, ["occ", "code"])

    area_col = _find_col(columns, ["AREA_TITLE", "AREA_NAME", "AREA"])
    if not area_col:
        area_col = _find_col_contains(columns, ["area"])

    if not tot_emp_col or not occ_code_col or not area_col:
        raise ValueError(
            "Unable to identify required OEWS columns. "
            f"Found: o_group={o_group_col}, tot_emp={tot_emp_col}, "
            f"occ_code={occ_code_col}, area={area_col}"
        )

    filtered = df.copy()
    if o_group_col:
        group_vals = filtered[o_group_col].astype(str).str.strip().str.lower()
        detailed_mask = group_vals.isin(
            ["detailed", "detail", "detailed occupations", "detailed occupation"]
        )
        if detailed_mask.any():
            filtered = filtered[detailed_mask].copy()

    filtered["employment"] = pd.to_numeric(
        filtered[tot_emp_col].astype(str).str.replace(",", ""),
        errors="coerce",
    )
    filtered["soc_code"] = filtered[occ_code_col].astype(str)
    filtered["region"] = filtered[area_col].astype(str)

    result = filtered[filtered["employment"] > 0][
        ["region", "soc_code", "employment"]
    ].dropna()
    print(
        f"  Cleaned OEWS ({year}): {len(result):,} rows, "
        f"{result['region'].nunique()} regions"
    )
    return result


def clean_projections_data(df: pd.DataFrame, year: str) -> pd.DataFrame:
    occ_type_col = [c for c in df.columns if "Occupation type" in c][0]
    matrix_code_col = [
        c
        for c in df.columns
        if "National Employment Matrix" in c and "code" in c.lower()
    ]
    sep_rate_col = [
        c
        for c in df.columns
        if "Total occupational separations" in c and "rate" in c.lower()
    ]

    if not matrix_code_col or not sep_rate_col:
        matrix_code_col = [
            c for c in df.columns if "Matrix" in c and ("code" in c.lower() or c.endswith("1"))
        ]
        sep_rate_col = [
            c for c in df.columns if "separation" in c.lower() and "rate" in c.lower()
        ]

    matrix_code_col = matrix_code_col[0] if matrix_code_col else None
    sep_rate_col = sep_rate_col[0] if sep_rate_col else None
    print(f"  Using columns: {occ_type_col}, {matrix_code_col}, {sep_rate_col}")

    filtered = df[df[occ_type_col].astype(str).str.strip() == "Line item"].copy()
    filtered["soc_code"] = filtered[matrix_code_col].apply(clean_soc_code)
    filtered["churn_rate"] = pd.to_numeric(filtered[sep_rate_col], errors="coerce")
    result = filtered[["soc_code", "churn_rate"]].dropna()
    print(f"  Cleaned Projections ({year}): {len(result):,} occupations")
    return result


def build_regional_skill_profiles(
    oews_df: pd.DataFrame, onet_df: pd.DataFrame
) -> pd.DataFrame:
    onet_avg = (
        onet_df.groupby(["soc_code", "feature_name"], as_index=False)["score"]
        .mean()
        .rename(columns={"score": "avg_score"})
    )
    merged = oews_df.merge(onet_avg, on="soc_code", how="inner")
    merged["weighted_score"] = merged["avg_score"] * merged["employment"]

    grouped = merged.groupby(["region", "feature_name"], as_index=False).agg(
        weighted_score=("weighted_score", "sum"),
        employment=("employment", "sum"),
    )
    grouped["weighted_score"] = grouped["weighted_score"] / grouped["employment"]
    return grouped[["region", "feature_name", "weighted_score"]]


def select_top_features(
    region_skills: pd.DataFrame, top_n: int, min_regions: int
) -> tuple[list[str], pd.DataFrame]:
    feature_stats = region_skills.groupby("feature_name").agg(
        variance=("weighted_score", "var"),
        n_regions=("region", "nunique"),
    )
    filtered = feature_stats[feature_stats["n_regions"] >= min_regions]
    top_features = filtered.nlargest(top_n, "variance").index.tolist()
    return top_features, filtered.loc[top_features].sort_values(
        "variance", ascending=False
    )


def pivot_to_wide(region_skills: pd.DataFrame, top_features: list[str]) -> pd.DataFrame:
    filtered = region_skills[region_skills["feature_name"].isin(top_features)].copy()
    pivoted = (
        filtered.pivot_table(
            index="region",
            columns="feature_name",
            values="weighted_score",
            aggfunc="mean",
        )
        .reset_index()
    )
    return pivoted


def build_regional_churn(oews_df: pd.DataFrame, churn_df: pd.DataFrame) -> pd.DataFrame:
    merged = oews_df.merge(churn_df, on="soc_code", how="inner")
    merged["weighted_churn"] = merged["churn_rate"] * merged["employment"]
    grouped = merged.groupby("region", as_index=False).agg(
        target_churn=("weighted_churn", "sum"),
        employment=("employment", "sum"),
    )
    grouped["target_churn"] = grouped["target_churn"] / grouped["employment"]
    return grouped[["region", "target_churn"]]


def create_analytical_table(X_df: pd.DataFrame, Y_df: pd.DataFrame) -> pd.DataFrame:
    merged = X_df.merge(Y_df, on="region", how="inner").dropna(subset=["target_churn"])
    return merged


def write_outputs(
    output_dir: Path,
    X_2019: pd.DataFrame,
    Y_2019: pd.DataFrame,
    Y_2023: pd.DataFrame,
    train_2019: pd.DataFrame,
    validate_2023: pd.DataFrame,
    feature_stats: pd.DataFrame,
    top_features: list[str],
    config: dict,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    X_2019.to_csv(output_dir / "X_2019.csv", index=False)
    Y_2019.to_csv(output_dir / "Y_2019.csv", index=False)
    Y_2023.to_csv(output_dir / "Y_2023.csv", index=False)
    train_2019.to_csv(output_dir / "train_2019.csv", index=False)
    validate_2023.to_csv(output_dir / "validate_2023.csv", index=False)
    feature_stats.reset_index().to_csv(output_dir / "feature_stats.csv", index=False)
    pd.DataFrame({"feature_name": top_features}).to_csv(
        output_dir / "top_features.csv", index=False
    )

    manifest = {
        "config": config,
        "rows": {
            "X_2019": int(len(X_2019)),
            "Y_2019": int(len(Y_2019)),
            "Y_2023": int(len(Y_2023)),
            "train_2019": int(len(train_2019)),
            "validate_2023": int(len(validate_2023)),
        },
    }
    with open(output_dir / "prep_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nOutputs saved to: {output_dir}")


def parse_args() -> argparse.Namespace:
    default_data_dir = Path(__file__).resolve().parent
    default_output_dir = default_data_dir / "prepared_data"
    default_workers = max(2, min(8, (os.cpu_count() or 4)))
    parser = argparse.ArgumentParser(
        description="Prepare False Growth Detector data locally."
    )
    parser.add_argument("--data-dir", default=default_data_dir, type=Path)
    parser.add_argument("--output-dir", default=default_output_dir, type=Path)
    parser.add_argument("--top-n-skills", default=100, type=int)
    parser.add_argument("--min-regions", default=50, type=int)
    parser.add_argument("--workers", default=default_workers, type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir
    output_dir = args.output_dir

    config = {
        "data_dir": str(data_dir),
        "output_dir": str(output_dir),
        "top_n_skills": args.top_n_skills,
        "min_regions": args.min_regions,
    }

    print("Loading input files...")
    raw = load_excel_files(data_dir, workers=args.workers)

    print("\nCleaning O*NET data...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(clean_onet_data, raw["onet_skills_19"], "19", "IM"): "onet_skills_19",
            executor.submit(clean_onet_data, raw["onet_context_19"], "19", "CX"): "onet_context_19",
            executor.submit(clean_onet_data, raw["onet_skills_23"], "23", "IM"): "onet_skills_23",
            executor.submit(clean_onet_data, raw["onet_context_23"], "23", "CX"): "onet_context_23",
        }
        results = {futures[f]: f.result() for f in as_completed(futures)}
    onet_skills_19 = results["onet_skills_19"]
    onet_context_19 = results["onet_context_19"]
    onet_skills_23 = results["onet_skills_23"]
    onet_context_23 = results["onet_context_23"]
    onet_clean_19 = pd.concat([onet_skills_19, onet_context_19], ignore_index=True)
    onet_clean_23 = pd.concat([onet_skills_23, onet_context_23], ignore_index=True)

    print("\nCleaning OEWS data...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(clean_oews_data, raw["bls_oews_19"], "19"): "oews_19",
            executor.submit(clean_oews_data, raw["bls_oews_23"], "23"): "oews_23",
        }
        results = {futures[f]: f.result() for f in as_completed(futures)}
    oews_clean_19 = results["oews_19"]
    oews_clean_23 = results["oews_23"]

    print("\nCleaning Projections data...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(clean_projections_data, raw["bls_proj_19"], "19"): "churn_19",
            executor.submit(clean_projections_data, raw["bls_proj_23"], "23"): "churn_23",
        }
        results = {futures[f]: f.result() for f in as_completed(futures)}
    churn_clean_19 = results["churn_19"]
    churn_clean_23 = results["churn_23"]

    print("\nBuilding regional skill profiles (2019)...")
    region_skills_19 = build_regional_skill_profiles(oews_clean_19, onet_clean_19)
    top_features, feature_stats = select_top_features(
        region_skills_19, args.top_n_skills, args.min_regions
    )
    X_2019 = pivot_to_wide(region_skills_19, top_features)

    print("\nBuilding regional churn targets...")
    Y_2019 = build_regional_churn(oews_clean_19, churn_clean_19)
    Y_2023 = build_regional_churn(oews_clean_23, churn_clean_23)

    print("\nCreating analytical tables...")
    train_2019 = create_analytical_table(X_2019, Y_2019)
    validate_2023 = create_analytical_table(X_2019, Y_2023)

    write_outputs(
        output_dir,
        X_2019,
        Y_2019,
        Y_2023,
        train_2019,
        validate_2023,
        feature_stats,
        top_features,
        config,
    )


if __name__ == "__main__":
    main()
