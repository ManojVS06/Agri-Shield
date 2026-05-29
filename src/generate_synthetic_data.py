"""Realistic synthetic agricultural subsidy fraud dataset generator using CTGAN.

Upgraded to use:
1. Multi-state (Pan-India) agricultural distribution statistics (from src/indian_agri_macro.py).
2. Tabular GAN (CTGAN) to model the multi-dimensional correlations of legitimate transactions.
3. Model caching to prevent slow training on every execution.
4. Smart entity mapping to assign real farmers and dealers to GAN-generated transactions.
5. Outlier-preserving fraud injection to ensure high-fidelity anomaly detection training.
"""
from __future__ import annotations

import argparse
import os
import sys
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# Add script directory to sys.path to enable local imports
sys.path.append(str(Path(__file__).parent))
try:
    from indian_agri_macro import STATE_MACRO_DATA, ALL_DISTRICT_CENTERS
except ImportError:
    # Fallback in case of execution context issues
    from src.indian_agri_macro import STATE_MACRO_DATA, ALL_DISTRICT_CENTERS


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CROP_TYPES    = ["Rice", "Wheat", "Cotton", "Maize", "Sugarcane", "Soybean"]
SUBSIDY_TYPES = ["Fertilizer", "Seed"]
PRODUCT_MAP   = {
    "Fertilizer": ["Urea", "DAP", "NPK", "MOP", "Superphosphate"],
    "Seed":       ["Hybrid Rice Seed", "Wheat Seed", "Cotton Seed",
                   "Maize Seed", "Soybean Seed", "BT Cotton Seed"],
}
PAYMENT_MODES = ["DBT", "Cash", "NEFT"]
SHOP_SIZES    = ["Small", "Medium", "Large"]
SEASONS       = ["Kharif", "Rabi", "Zaid"]

FIRST_NAMES = ["Aarav","Vikram","Rahul","Suresh","Ramesh","Anita","Pooja",
               "Meera","Kavita","Sunita","Farhan","Imran","Ganesh","Lakshmi",
               "Priya","Santosh","Bharat","Ravi","Deepak","Sonal"]
LAST_NAMES  = ["Patil","Sharma","Yadav","Reddy","Singh","Khan","Jadhav",
               "Naik","Verma","Pawar","Desai","More","Shinde","Gaikwad","Kulkarni"]


@dataclass(frozen=True)
class Config:
    n_farmers:      int   = 4500
    n_dealers:      int   = 380
    n_transactions: int   = 15000
    fraud_ratio:    float = 0.13
    random_seed:    int   = 42
    epochs:         int   = 10
    retrain:        bool  = False
    model_path:     Path  = Path("models/ctgan_generator.pkl")


def _choice(rng, values, size):
    return rng.choice(values, size=size)


def _season_for_date(ts):
    m = ts.month
    if m in {6,7,8,9,10}: return "Kharif"
    if m in {11,12,1,2,3}: return "Rabi"
    return "Zaid"


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0; p = np.pi/180
    dlat = (lat2-lat1)*p; dlon = (lon2-lon1)*p
    a = np.sin(dlat/2)**2 + np.cos(lat1*p)*np.cos(lat2*p)*np.sin(dlon/2)**2
    return np.round(2*R*np.arcsin(np.sqrt(a)), 2)


# ---------------------------------------------------------------------------
# Entity generators (Macro-Anchored)
# ---------------------------------------------------------------------------

def generate_farmers(cfg: Config, rng: np.random.Generator) -> pd.DataFrame:
    """Generate farmers anchored by real-world multi-state macro statistics."""
    ids = np.arange(1, cfg.n_farmers + 1)
    
    # State mapping based on weights
    states_list = list(STATE_MACRO_DATA.keys())
    state_weights = [STATE_MACRO_DATA[s]["weight"] for s in states_list]
    state_weights = np.array(state_weights) / sum(state_weights)
    
    chosen_states = rng.choice(states_list, size=cfg.n_farmers, p=state_weights)
    
    districts = []
    crops = []
    land = []
    villages = []
    soil_types = []
    irrigation_types = []
    lats = []
    lons = []
    
    for state in chosen_states:
        info = STATE_MACRO_DATA[state]
        # District
        dist = rng.choice(list(info["districts"].keys()))
        districts.append(dist)
        # Crop
        crop_list = list(info["crops"].keys())
        crop_w = [info["crops"][c] for c in crop_list]
        crop_w = np.array(crop_w) / sum(crop_w)
        crops.append(rng.choice(crop_list, p=crop_w))
        # Land
        mu, sigma = info["land_lognormal_mu"], info["land_lognormal_sigma"]
        l_val = np.clip(rng.lognormal(mu, sigma), 0.1, 15.0)
        land.append(l_val)
        # Village
        villages.append(rng.choice(info["villages"]))
        # Soil
        soil_types.append(rng.choice(info["soil_types"]))
        # Irrigation
        irrigation_types.append(rng.choice(info["irrigation_types"]))
        # Lat/Long
        base_lat, base_lon = info["districts"][dist]
        lats.append(base_lat + rng.normal(0, 0.07))
        lons.append(base_lon + rng.normal(0, 0.07))
        
    land = np.array(land)
    # ~3% ghost farmers with land=0 mixed into legit population
    ghost_mask = rng.random(cfg.n_farmers) < 0.03
    land[ghost_mask] = 0.0
    land = np.round(land, 2)
    
    aadhaar  = [f"aadhaar_{rng.integers(10**11, 10**12-1)}" for _ in ids]
    names    = [f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}" for _ in ids]
    
    df = pd.DataFrame({
        "farmer_id":          ids,
        "aadhaar_hash":       aadhaar,
        "name":               names,
        "state":              chosen_states,
        "district":           districts,
        "village":            villages,
        "land_size_acres":    land,
        "crop_type":          crops,
        "irrigation_type":    irrigation_types,
        "soil_type":          soil_types,
        "bank_account":       [f"BANK{rng.integers(10**9,10**10-1)}" for _ in ids],
        "mobile_number":      [f"9{rng.integers(10**9,10**10-1)}" for _ in ids],
        "registration_year":  rng.integers(2018, 2024, cfg.n_farmers),
        "income_category":    rng.choice(["BPL","APL","Marginal","Small","Large"], cfg.n_farmers),
        "farmer_location_lat": lats,
        "farmer_location_long":lons,
    })
    return df


def generate_dealers(cfg: Config, rng: np.random.Generator) -> pd.DataFrame:
    """Generate dealers anchored by real-world multi-state macro statistics."""
    ids = np.arange(1, cfg.n_dealers + 1)
    
    states_list = list(STATE_MACRO_DATA.keys())
    state_weights = [STATE_MACRO_DATA[s]["weight"] for s in states_list]
    state_weights = np.array(state_weights) / sum(state_weights)
    
    chosen_states = rng.choice(states_list, size=cfg.n_dealers, p=state_weights)
    
    districts = []
    lats = []
    lons = []
    license_numbers = []
    gst_numbers = []
    
    state_gst_codes = {
        "Maharashtra": "27",
        "Punjab": "03",
        "Uttar Pradesh": "09",
        "Andhra Pradesh": "37",
        "West Bengal": "19"
    }
    
    state_lic_prefixes = {
        "Maharashtra": "MH-AGR",
        "Punjab": "PB-AGR",
        "Uttar Pradesh": "UP-AGR",
        "Andhra Pradesh": "AP-AGR",
        "West Bengal": "WB-AGR"
    }
    
    for state in chosen_states:
        info = STATE_MACRO_DATA[state]
        dist = rng.choice(list(info["districts"].keys()))
        districts.append(dist)
        
        base_lat, base_lon = info["districts"][dist]
        lats.append(base_lat + rng.normal(0, 0.05))
        lons.append(base_lon + rng.normal(0, 0.05))
        
        license_numbers.append(f"{state_lic_prefixes[state]}-{rng.integers(10**6,10**7-1)}")
        gst_prefix = state_gst_codes[state]
        gst_numbers.append(f"{gst_prefix}AAAA{rng.integers(1000,9999)}Z{rng.integers(1,9)}")
        
    df = pd.DataFrame({
        "dealer_id":      ids,
        "dealer_name":    [f"AgriMart_{i:04d}" for i in ids],
        "state":          chosen_states,
        "district":       districts,
        "license_number": license_numbers,
        "shop_size":      _choice(rng, SHOP_SIZES, cfg.n_dealers),
        "years_active":   rng.integers(1, 30, cfg.n_dealers),
        "gst_number":     gst_numbers,
        "avg_daily_sales":np.round(rng.uniform(8000, 200000, cfg.n_dealers), 2),
        "dealer_location_lat": lats,
        "dealer_location_long": lons,
    })
    return df


# ---------------------------------------------------------------------------
# Seed Data Generation (Legitimate Baseline)
# ---------------------------------------------------------------------------

def generate_legit_seed_transactions(cfg: Config, rng: np.random.Generator, farmers: pd.DataFrame, dealers: pd.DataFrame, n_seed: int = 4000) -> pd.DataFrame:
    """Generate high-fidelity clean transactions to act as seed data for CTGAN."""
    # Weighted farmer sampling (smaller farmers transact more often)
    fw = 1.0 / (farmers["land_size_acres"].clip(lower=0.05) ** 0.5)
    fw /= fw.sum()
    f_idx = rng.choice(farmers.index, n_seed, p=fw)
    
    # Pareto dealer distribution
    dp = rng.pareto(2.0, cfg.n_dealers) + 1; dp /= dp.sum()
    d_idx = rng.choice(dealers.index, n_seed, p=dp)
    
    seed_txns = []
    for i in range(n_seed):
        farmer = farmers.iloc[f_idx[i]]
        # Find dealer in the same district or state to represent clean local shopping
        dealer_pool = dealers[dealers["district"] == farmer["district"]]
        if dealer_pool.empty:
            dealer_pool = dealers[dealers["state"] == farmer["state"]]
        if dealer_pool.empty:
            dealer_pool = dealers
        dealer = dealer_pool.iloc[rng.choice(len(dealer_pool))]
        
        # Product type map aligned with crop
        sub_type = rng.choice(SUBSIDY_TYPES)
        if sub_type == "Seed" and farmer["crop_type"] != "Sugarcane":
            # Map seed product specifically to farmer's crop
            prod_candidates = [p for p in PRODUCT_MAP["Seed"] if farmer["crop_type"] in p]
            prod_type = rng.choice(prod_candidates) if prod_candidates else rng.choice(PRODUCT_MAP["Seed"])
        else:
            # Sugarcane or Fertilizer type
            prod_type = rng.choice(PRODUCT_MAP["Fertilizer"])
            sub_type = "Fertilizer"
            
        # Crop-specific quantity densities (legit quantity correlates with land size and crop)
        density = {
            "Sugarcane": rng.uniform(15.0, 30.0),
            "Rice":      rng.uniform(6.0, 12.0),
            "Wheat":     rng.uniform(5.0, 10.0),
            "Soybean":   rng.uniform(3.0, 6.0),
            "Cotton":    rng.uniform(2.0, 5.0),
            "Maize":     rng.uniform(3.0, 7.0),
        }.get(farmer["crop_type"], 5.0)
        
        qty = np.maximum(1.0, farmer["land_size_acres"] * density + rng.normal(0, 1.5))
        
        unit_sub = rng.uniform(7, 16) if sub_type == "Fertilizer" else rng.uniform(12, 25)
        subsidy_amount = round(qty * unit_sub, 2)
        actual_price = round(subsidy_amount * rng.uniform(1.2, 1.7), 2)
        
        # Season calendar month based on crop
        month = {
            "Rice":      int(rng.choice([6, 7, 8, 11, 12], p=[0.35, 0.35, 0.1, 0.1, 0.1])),
            "Wheat":     int(rng.choice([10, 11, 12, 1], p=[0.1, 0.4, 0.4, 0.1])),
            "Cotton":    int(rng.choice([5, 6, 7], p=[0.2, 0.5, 0.3])),
            "Maize":     int(rng.choice([6, 7, 10, 11], p=[0.3, 0.3, 0.2, 0.2])),
            "Sugarcane": int(rng.choice([1, 2, 3, 10, 11], p=[0.2, 0.2, 0.2, 0.2, 0.2])),
            "Soybean":   int(rng.choice([6, 7, 8], p=[0.4, 0.4, 0.2])),
        }.get(farmer["crop_type"], 6)
        
        # Season based on month
        season = "Kharif" if month in {6,7,8,9,10} else "Rabi" if month in {11,12,1,2,3} else "Zaid"
        
        # Date generation with hour
        year = rng.choice([2023, 2024, 2025])
        day = rng.integers(1, 28)
        hour = rng.integers(8, 18) # Clean normal business hours
        dt = pd.Timestamp(f"{year}-{month:02d}-{day:02d} {hour:02d}:00:00")
        
        days_since_start = (dt - pd.Timestamp("2023-01-01")).total_seconds() / 86400.0
        
        seed_txns.append({
            "district":       farmer["district"],
            "crop_type":      farmer["crop_type"],
            "land_size_acres":farmer["land_size_acres"],
            "subsidy_type":   sub_type,
            "product_type":   prod_type,
            "quantity":       qty,
            "subsidy_amount": subsidy_amount,
            "actual_price":   actual_price,
            "payment_mode":   rng.choice(PAYMENT_MODES, p=[0.75, 0.18, 0.07]),
            "season":         season,
            "transaction_hour":hour,
            "day_of_week":    dt.day_name(),
            "transaction_month":month,
            "days_since_start":days_since_start
        })
        
    return pd.DataFrame(seed_txns)


# ---------------------------------------------------------------------------
# CTGAN Training and Sampling Pipeline
# ---------------------------------------------------------------------------

def train_or_load_ctgan(cfg: Config, seed_data: pd.DataFrame) -> any:
    """Train CTGAN model or load cached version if it exists."""
    discrete_columns = [
        "district",
        "crop_type",
        "subsidy_type",
        "product_type",
        "payment_mode",
        "season",
        "day_of_week"
    ]
    
    # Check if cached model exists
    if cfg.model_path.exists() and not cfg.retrain:
        print(f"[GAN] Loading cached CTGAN synthesizer from {cfg.model_path}...")
        try:
            with open(cfg.model_path, "rb") as f:
                synthesizer = pickle.load(f)
            return synthesizer
        except Exception as e:
            print(f"[GAN] Error loading cached model: {e}. Retraining...")
            
    print(f"[GAN] Preparing CTGAN training on {len(seed_data)} seed records...")
    
    # Import CTGAN locally to give descriptive error if missing
    try:
        from ctgan import CTGAN
    except ImportError:
        print("\n" + "!" * 80)
        print("CRITICAL ERROR: 'ctgan' package is not installed in the virtual environment!")
        print("Please run: .\\.venv\\Scripts\\pip install ctgan")
        print("!" * 80 + "\n")
        sys.exit(1)
        
    # We choose a small batch size and epochs for faster CPU training
    synthesizer = CTGAN(epochs=cfg.epochs, verbose=True, batch_size=250)
    synthesizer.fit(seed_data, discrete_columns=discrete_columns)
    
    # Cache model
    cfg.model_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg.model_path, "wb") as f:
        pickle.dump(synthesizer, f)
    print(f"[GAN] Saved trained CTGAN synthesizer to {cfg.model_path}")
    
    return synthesizer


def postprocess_sampled_data(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Post-process GAN output to fix boundary violations and compute datetimes."""
    df = df.copy()
    
    # Clip numerical fields to realistic ranges
    df["land_size_acres"] = np.clip(df["land_size_acres"].fillna(2.0), 0.1, 15.0).round(2)
    df["quantity"] = np.clip(df["quantity"].fillna(10.0), 1.0, 500.0).round(2)
    df["subsidy_amount"] = np.clip(df["subsidy_amount"].fillna(100.0), 10.0, 100000.0).round(2)
    df["actual_price"] = np.clip(df["actual_price"].fillna(150.0), 10.0, 200000.0).round(2)
    
    # Convert days_since_start to datetime
    days_since_start = np.clip(df["days_since_start"].fillna(rng.uniform(0, 1095)), 0.0, 1095.0)
    start_date = pd.Timestamp("2023-01-01")
    df["date"] = start_date + pd.to_timedelta(days_since_start, unit="D")
    
    # Clean hour and month
    df["transaction_hour"] = np.clip(df["transaction_hour"].fillna(12).round().astype(int), 0, 23)
    df["transaction_month"] = np.clip(df["transaction_month"].fillna(6).round().astype(int), 1, 12)
    
    # Adjust hour on date
    df["date"] = df["date"].dt.normalize() + pd.to_timedelta(df["transaction_hour"], unit="h") + pd.to_timedelta(rng.integers(0, 60, len(df)), unit="m")
    
    # Clean discrete columns
    for col in ["district", "crop_type", "subsidy_type", "product_type", "payment_mode", "season", "day_of_week"]:
        if col in df.columns:
            nulls = df[col].isna()
            if nulls.any():
                non_null_vals = df[col].dropna().unique()
                if len(non_null_vals) == 0:
                    if col == "crop_type": non_null_vals = CROP_TYPES
                    elif col == "subsidy_type": non_null_vals = SUBSIDY_TYPES
                    elif col == "payment_mode": non_null_vals = PAYMENT_MODES
                    elif col == "season": non_null_vals = SEASONS
                    elif col == "day_of_week": non_null_vals = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    else: non_null_vals = ["Unknown"]
                df.loc[nulls, col] = rng.choice(non_null_vals, size=nulls.sum())
                
    return df


def assign_entities_to_sampled_txns(sampled_txns: pd.DataFrame, farmers: pd.DataFrame, dealers: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Map sampled GAN transactions back to actual farmer and dealer records."""
    # Pre-group farmers and dealers by district
    farmers_by_district = {d: grp for d, grp in farmers.groupby("district")}
    dealers_by_district = {d: grp for d, grp in dealers.groupby("district")}
    
    farmer_ids = []
    dealer_ids = []
    
    print("[MAP] Matching farmers and dealers to CTGAN transactions...")
    for _, row in sampled_txns.iterrows():
        dist = row["district"]
        crop = row["crop_type"]
        target_land = row["land_size_acres"]
        
        # 1. Match Farmer
        f_pool = farmers_by_district.get(dist, farmers)
        if f_pool.empty:
            f_pool = farmers
            
        f_crop_pool = f_pool[f_pool["crop_type"] == crop]
        if not f_crop_pool.empty:
            f_pool = f_crop_pool
            
        # Find farmer with closest land size
        land_diffs = (f_pool["land_size_acres"] - target_land).abs()
        best_farmer_idx = land_diffs.idxmin()
        farmer_ids.append(f_pool.loc[best_farmer_idx, "farmer_id"])
        
        # 2. Match Dealer (geographic constraint: same district)
        d_pool = dealers_by_district.get(dist, dealers)
        if d_pool.empty:
            # Fallback to same state
            state = farmers[farmers["farmer_id"] == farmer_ids[-1]]["state"].values[0]
            d_pool = dealers[dealers["state"] == state]
        if d_pool.empty:
            d_pool = dealers
            
        chosen_dealer_id = rng.choice(d_pool["dealer_id"].values)
        dealer_ids.append(chosen_dealer_id)
        
    sampled_txns["farmer_id"] = farmer_ids
    sampled_txns["dealer_id"] = dealer_ids
    
    # Overwrite transaction metadata columns to match farmer and dealer exactly
    sampled_txns.drop(columns=["district", "land_size_acres", "crop_type"], inplace=True)
    
    sampled_txns = sampled_txns.merge(
        farmers[["farmer_id", "district", "land_size_acres", "crop_type", "aadhaar_hash",
                 "farmer_location_lat", "farmer_location_long", "income_category", "irrigation_type"]],
        on="farmer_id", how="left"
    )
    
    sampled_txns = sampled_txns.merge(
        dealers[["dealer_id", "dealer_location_lat", "dealer_location_long", "shop_size"]],
        on="dealer_id", how="left"
    )
    
    return sampled_txns


# ---------------------------------------------------------------------------
# Fraud injection — realistic pan-India overlapping patterns
# ---------------------------------------------------------------------------

def inject_fraud(cfg: Config, rng: np.random.Generator, txns: pd.DataFrame, farmers: pd.DataFrame):
    """Inject 8 types of agricultural subsidy fraud."""
    n_fraud = int(len(txns) * cfg.fraud_ratio)
    
    # Stratified weighting: fraud is more likely on borderline transactions
    weights = (txns["subsidy_per_acre"].clip(upper=500) / 500 +
               (txns["distance_farmer_dealer"] / 600).clip(upper=1)) * 0.5 + 0.5
    weights /= weights.sum()
    fraud_idx = rng.choice(txns.index, size=n_fraud, replace=False, p=weights)
    
    splits = np.array_split(rng.permutation(fraud_idx), [
        int(n_fraud*0.18),   # ghost farmer
        int(n_fraud*0.34),   # over-claiming
        int(n_fraud*0.48),   # dealer collusion
        int(n_fraud*0.60),   # geo fraud
        int(n_fraud*0.70),   # duplicate identity
        int(n_fraud*0.80),   # time burst
        int(n_fraud*0.90),   # fake transactions
    ])
    
    # 1. Ghost Farmer
    idx = splits[0]
    land_vals = rng.choice([0.0, 0.0, 0.0, 0.05, 0.08, 0.1], len(idx))
    txns.loc[idx, "land_size_acres"] = land_vals
    txns.loc[idx, "risk_score"]  = rng.integers(55, 89, len(idx))
    txns.loc[idx, "is_fraud"]    = 1
    txns.loc[idx, "fraud_type"]  = "Ghost Farmer"
    txns.loc[idx, "fraud_reason"]= "Land size inconsistent with subsidy claimed"
    
    # 2. Over-claiming
    idx = splits[1]
    mult = rng.uniform(1.4, 2.5, len(idx))
    txns.loc[idx, "quantity"]       = np.round(txns.loc[idx, "quantity"] * mult, 2)
    txns.loc[idx, "subsidy_amount"] = np.round(txns.loc[idx, "subsidy_amount"] * rng.uniform(1.3, 2.2, len(idx)), 2)
    txns.loc[idx, "risk_score"]  = rng.integers(52, 87, len(idx))
    txns.loc[idx, "is_fraud"]    = 1
    txns.loc[idx, "fraud_type"]  = "Over-claiming"
    txns.loc[idx, "fraud_reason"]= "Claimed quantity exceeds land capacity"
    
    # 3. Dealer Collusion
    idx = splits[2]
    top_dealers = txns.groupby("dealer_id")["txn_id"].count().nlargest(5).index.tolist()
    assigned    = rng.choice(top_dealers, len(idx))
    txns.loc[idx, "dealer_id"]   = assigned
    txns.loc[idx, "risk_score"]  = rng.integers(50, 83, len(idx))
    txns.loc[idx, "is_fraud"]    = 1
    txns.loc[idx, "fraud_type"]  = "Dealer Collusion"
    txns.loc[idx, "fraud_reason"]= "Routed through high-volume suspicious dealer"
    
    # 4. Geo Fraud
    idx = splits[3]
    if len(idx):
        anchor_lat = float(txns.loc[idx, "farmer_location_lat"].median())
        anchor_lon = float(txns.loc[idx, "farmer_location_long"].median())
        txns.loc[idx, "farmer_location_lat"]  = anchor_lat + rng.normal(0, 0.015, len(idx))
        txns.loc[idx, "farmer_location_long"] = anchor_lon + rng.normal(0, 0.015, len(idx))
        txns.loc[idx, "geo_lat"]  = anchor_lat
        txns.loc[idx, "geo_long"] = anchor_lon
    txns.loc[idx, "risk_score"]  = rng.integers(48, 82, len(idx))
    txns.loc[idx, "is_fraud"]    = 1
    txns.loc[idx, "fraud_type"]  = "Geo Fraud"
    txns.loc[idx, "fraud_reason"]= "Farmers clustered at suspicious coordinates"
    
    # 5. Duplicate Identity (Aadhaar reuse)
    idx = splits[4]
    dup_pool = rng.choice(farmers["aadhaar_hash"].to_numpy(), size=max(1, len(idx)//4))
    txns.loc[idx, "aadhaar_hash"] = rng.choice(dup_pool, len(idx), replace=True)
    txns.loc[idx, "risk_score"]  = rng.integers(48, 80, len(idx))
    txns.loc[idx, "is_fraud"]    = 1
    txns.loc[idx, "fraud_type"]  = "Duplicate Identity"
    txns.loc[idx, "fraud_reason"]= "Aadhaar reused across multiple farmer accounts"
    
    # 6. Time Burst
    idx = splits[5]
    if len(idx):
        burst_start = pd.Timestamp("2024-11-20 09:00:00")
        offsets     = rng.integers(0, 120, len(idx))
        txns.loc[idx, "date"]             = burst_start + pd.to_timedelta(offsets, unit="m")
        txns.loc[idx, "transaction_hour"] = txns.loc[idx, "date"].dt.hour
        txns.loc[idx, "day_of_week"]      = txns.loc[idx, "date"].dt.day_name()
        txns.loc[idx, "days_since_last_txn"] = np.round(rng.uniform(0.01, 2.0, len(idx)), 2)
    txns.loc[idx, "risk_score"]  = rng.integers(46, 79, len(idx))
    txns.loc[idx, "is_fraud"]    = 1
    txns.loc[idx, "fraud_type"]  = "Time Burst Fraud"
    txns.loc[idx, "fraud_reason"]= "High transaction frequency in short time window"
    
    # 7. Fake Transactions (actual_price very low)
    idx = splits[6]
    fake_price = np.round(txns.loc[idx, "subsidy_amount"] * rng.uniform(0.0, 0.12, len(idx)), 2)
    txns.loc[idx, "actual_price"] = fake_price
    txns.loc[idx, "payment_mode"] = rng.choice(["Cash","Cash","NEFT"], len(idx))
    txns.loc[idx, "risk_score"]   = rng.integers(55, 88, len(idx))
    txns.loc[idx, "is_fraud"]     = 1
    txns.loc[idx, "fraud_type"]   = "Fake Transactions"
    txns.loc[idx, "fraud_reason"] = "No corresponding product sale or very low actual price"
    
    # 8. Off-Season Fraud
    idx = splits[7]
    if len(idx):
        off_dates   = pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(90,140,len(idx)), unit="D") # April/May
        txns.loc[idx, "date"]    = off_dates
        txns.loc[idx, "season"]  = "Zaid"
        txns.loc[idx, "seasonality_index"] = 0.75
    txns.loc[idx, "risk_score"]  = rng.integers(44, 76, len(idx))
    txns.loc[idx, "is_fraud"]    = 1
    txns.loc[idx, "fraud_type"]  = "Off-Season Fraud"
    txns.loc[idx, "fraud_reason"]= "Subsidy claimed outside valid crop season"


# ---------------------------------------------------------------------------
# Output operations
# ---------------------------------------------------------------------------

def save_outputs(out_dir: Path, farmers: pd.DataFrame, dealers: pd.DataFrame, txns: pd.DataFrame):
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Drop intermediate execution helper columns (like state) to preserve exact original schemas
    farmers_out = farmers.drop(columns=["state"], errors="ignore")
    dealers_out = dealers.drop(columns=["state"], errors="ignore")
    
    farmers_out.to_csv(out_dir / "farmers.csv", index=False)
    dealers_out.to_csv(out_dir / "dealers.csv", index=False)
    txns.to_csv(out_dir / "transactions.csv", index=False)


# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows",        type=int,   default=15000)
    parser.add_argument("--fraud-ratio", type=float, default=0.13)
    parser.add_argument("--seed",        type=int,   default=42)
    parser.add_argument("--output",      type=Path,  default=Path("data"))
    parser.add_argument("--epochs",      type=int,   default=10, help="CTGAN training epochs")
    parser.add_argument("--retrain",     action="store_true", help="Force CTGAN retraining")
    args = parser.parse_args()

    cfg = Config(
        n_transactions=args.rows,
        fraud_ratio=args.fraud_ratio,
        random_seed=args.seed,
        epochs=args.epochs,
        retrain=args.retrain
    )
    rng = np.random.default_rng(cfg.random_seed)

    print("\n" + "="*70)
    print("  GENERATING SYNTHETIC NATIONAL AGRICUTURAL SUBSIDY DATASET (CTGAN)")
    print("="*70)

    # 1. Generate core entities
    print("[INIT] Generating farmers and dealers...")
    farmers = generate_farmers(cfg, rng)
    dealers = generate_dealers(cfg, rng)
    
    # 2. Generate Legitimate seed data
    print("[INIT] Generating seed transactions for GAN anchor...")
    seed_txns = generate_legit_seed_transactions(cfg, rng, farmers, dealers, n_seed=4000)
    
    # 3. Train or load CTGAN
    ctgan_model = train_or_load_ctgan(cfg, seed_txns)
    
    # 4. Sample transactions from CTGAN
    print(f"[GAN] Sampling {cfg.n_transactions} transactions from CTGAN model...")
    sampled_txns = ctgan_model.sample(cfg.n_transactions)
    
    # 5. Postprocess & map entities
    print("[POST] Postprocessing sampled transactions and mapping entities...")
    sampled_txns = postprocess_sampled_data(sampled_txns, rng)
    txns = assign_entities_to_sampled_txns(sampled_txns, farmers, dealers, rng)
    
    # 6. Re-calculate metrics and distance before fraud injection
    txns["txn_id"] = np.arange(1, len(txns) + 1)
    txns["distance_farmer_dealer"] = _haversine(
        txns["farmer_location_lat"].to_numpy(),
        txns["farmer_location_long"].to_numpy(),
        txns["dealer_location_lat"].to_numpy(),
        txns["dealer_location_long"].to_numpy()
    )
    txns["geo_lat"]  = np.round((txns["farmer_location_lat"] + txns["dealer_location_lat"])/2, 6)
    txns["geo_long"] = np.round((txns["farmer_location_long"] + txns["dealer_location_long"])/2, 6)
    
    txns["season"] = txns["date"].apply(_season_for_date)
    txns["transaction_hour"] = txns["date"].dt.hour
    txns["day_of_week"]      = txns["date"].dt.day_name()
    txns["transaction_month"]= txns["date"].dt.month
    txns["seasonality_index"]= np.where(txns["season"]=="Kharif", 1.15,
                               np.where(txns["season"]=="Rabi",   0.95, 1.05))
    
    txns = txns.sort_values(["farmer_id","date"]).reset_index(drop=True)
    txns["days_since_last_txn"] = (
        txns.groupby("farmer_id")["date"].diff().dt.total_seconds().div(86400)
    ).fillna(999).round(2)
    
    # Base risk scores (legitimate distributions)
    txns["is_fraud"]    = 0
    txns["fraud_type"]  = "None"
    txns["fraud_reason"]= "Normal behavior"
    txns["risk_score"]  = rng.integers(5, 46, len(txns))
    
    # Derived baseline features
    txns["subsidy_per_acre"]       = np.round(txns["subsidy_amount"] / txns["land_size_acres"].clip(lower=0.1), 3)
    txns["transactions_per_farmer"]= txns.groupby("farmer_id")["txn_id"].transform("count")
    txns["dealer_farmers_count"]   = txns.groupby("dealer_id")["farmer_id"].transform("nunique")
    txns["avg_quantity_per_farmer"] = txns.groupby("farmer_id")["quantity"].transform("mean").round(2)

    # 7. Inject fraud outliers
    print("[FRAUD] Injecting fraud patterns into GAN baseline...")
    inject_fraud(cfg, rng, txns, farmers)
    
    # 8. Add label noise (2% audit misclassification)
    print("[FRAUD] Fuzzing audit labels (2% label noise)...")
    noise_idx = rng.choice(txns.index, size=int(0.02 * len(txns)), replace=False)
    txns.loc[noise_idx, "is_fraud"] = 1 - txns.loc[noise_idx, "is_fraud"]
    flipped_fraud = noise_idx[txns.loc[noise_idx, "is_fraud"] == 1]
    txns.loc[flipped_fraud, "fraud_type"]  = "Audit Reclassification"
    txns.loc[flipped_fraud, "fraud_reason"]= "Flagged by auditor review"
    txns.loc[flipped_fraud, "risk_score"]  = rng.integers(50, 75, len(flipped_fraud))
    
    txns = txns.sort_values("txn_id").reset_index(drop=True)
    
    # Save files
    print(f"[SAVE] Writing generated files to {args.output.resolve()}...")
    save_outputs(args.output, farmers, dealers, txns)
    
    print("\n" + "="*70)
    print("  SYNTHETIC DATASET GENERATION SUCCESSFUL")
    print("="*70)
    print(f"Generated farmers:     {len(farmers)}")
    print(f"Generated dealers:     {len(dealers)}")
    print(f"Generated transactions:{len(txns)}")
    print(f"Fraud rows:            {int(txns['is_fraud'].sum())} "
          f"({txns['is_fraud'].mean()*100:.1f}%)")
    print(f"Fraud types:\n{txns[txns['is_fraud']==1]['fraud_type'].value_counts().to_string()}")
    print(f"States represented:    {', '.join(farmers['state'].unique()) if 'state' in farmers.columns else 'Pan-India'}")
    print(f"Saved to: {args.output.resolve()}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
