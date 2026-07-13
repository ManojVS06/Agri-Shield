import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

def engineer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series | None, list[str], dict]:
    df = df.copy()
    label_encoders: dict[str, LabelEncoder] = {}

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["txn_month"]    = df["date"].dt.month
        df["txn_quarter"]  = df["date"].dt.quarter
        df["txn_dow"]      = df["date"].dt.dayofweek
        df["txn_hour"]     = df["date"].dt.hour
        df["txn_is_weekend"] = (df["txn_dow"] >= 5).astype(int)
        df["month_sin"]    = np.sin(2 * np.pi * df["txn_month"] / 12)
        df["month_cos"]    = np.cos(2 * np.pi * df["txn_month"] / 12)
        df["hour_sin"]     = np.sin(2 * np.pi * df["txn_hour"] / 24)
        df["hour_cos"]     = np.cos(2 * np.pi * df["txn_hour"] / 24)
        df["hour_bin"]     = pd.cut(df["txn_hour"],
                                    bins=[0,6,12,18,24], labels=[0,1,2,3],
                                    right=False).astype(float).fillna(0)
        df.drop(columns=["date"], inplace=True)

    eps = 1e-6

    # Ratio features
    if "subsidy_amount" in df.columns and "land_size_acres" in df.columns:
        df["subsidy_per_acre"]    = df["subsidy_amount"] / (df["land_size_acres"] + eps)
    if "actual_price" in df.columns and "subsidy_amount" in df.columns:
        df["price_subsidy_ratio"] = df["actual_price"] / (df["subsidy_amount"] + eps)
    if "quantity" in df.columns and "land_size_acres" in df.columns:
        df["quantity_per_acre"]   = df["quantity"] / (df["land_size_acres"] + eps)
    if "quantity" in df.columns and "distance_farmer_dealer" in df.columns:
        df["qty_x_distance"]      = df["quantity"] * df["distance_farmer_dealer"]
    if "actual_price" in df.columns:
        df["price_near_zero"]     = (df["actual_price"] < 10).astype(int)
    if "land_size_acres" in df.columns:
        df["land_is_zero"]        = (df["land_size_acres"] < 0.05).astype(int)

    # Group aggregations
    for col, grp in [("subsidy_amount", "farmer_id"), ("quantity", "farmer_id"),
                     ("subsidy_amount", "dealer_id"), ("quantity", "dealer_id")]:
        if col in df.columns and grp in df.columns:
            g = df.groupby(grp)[col]
            pfx = f"{col}_by_{grp}"
            df[f"{pfx}_mean"] = g.transform("mean")
            df[f"{pfx}_std"]  = g.transform("std").fillna(0)
            df[f"{pfx}_max"]  = g.transform("max")
            df[f"{pfx}_zscore"] = (df[col] - df[f"{pfx}_mean"]) / (df[f"{pfx}_std"] + eps)

    if "dealer_id" in df.columns and "farmer_id" in df.columns:
        df["dealer_unique_farmers"] = df.groupby("dealer_id")["farmer_id"].transform("nunique")
    if "farmer_id" in df.columns:
        df["farmer_txn_count"] = df.groupby("farmer_id")["farmer_id"].transform("count")
    if "dealer_id" in df.columns:
        df["dealer_txn_count"] = df.groupby("dealer_id")["dealer_id"].transform("count")
    if "dealer_id" in df.columns and "farmer_id" in df.columns:
        df["dealer_farmer_ratio"] = df["dealer_unique_farmers"] / (df["dealer_txn_count"] + eps)

    if "distance_farmer_dealer" in df.columns:
        df["distance_log"] = np.log1p(df["distance_farmer_dealer"])
        df["distance_bin"] = pd.qcut(df["distance_farmer_dealer"], q=5,
                                     labels=False, duplicates="drop").fillna(0)

    # District-level fraud rate encoding (target encoding proxy using stats)
    if "district" in df.columns and "subsidy_per_acre" in df.columns:
        dist_mean = df.groupby("district")["subsidy_per_acre"].transform("mean")
        df["district_subsidy_mean"] = dist_mean

    drop_cols = ["txn_id", "is_fraud", "fraud_type", "fraud_reason", "aadhaar_hash",
                 "farmer_location_lat", "farmer_location_long",
                 "dealer_location_lat", "dealer_location_long",
                 "geo_lat", "geo_long", "farmer_id", "dealer_id",
                 "bank_account", "mobile_number", "name"]
    target = df["is_fraud"].copy() if "is_fraud" in df.columns else None
    df.drop(columns=[c for c in drop_cols if c in df.columns], inplace=True)

    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    for col in cat_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        label_encoders[col] = le

    df.fillna(0, inplace=True)
    return df, target, df.columns.tolist(), label_encoders
