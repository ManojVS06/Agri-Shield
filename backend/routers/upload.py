"""CSV upload and pipeline trigger endpoints."""
import io
import os
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session

import models
from database import get_db, engine
from ml_service import ml_service

router = APIRouter(prefix="/api/upload", tags=["upload"])

DATA_DIR  = Path(os.getenv("DATA_DIR",  "../data"))
MODEL_PATH= Path(os.getenv("MODEL_PATH","../models/fraud_detector.pkl"))

_log_buffer: list[str] = []


def _log(msg: str):
    _log_buffer.append(msg)
    print(msg)


@router.get("/logs")
def get_processing_logs():
    return {"logs": _log_buffer[-100:]}


@router.post("/csv")
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files accepted")
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(400, f"Could not parse CSV: {e}")

    _log_buffer.clear()
    background_tasks.add_task(_seed_transactions, df, db)
    return {"message": f"Uploaded {len(df)} rows. Processing started.", "rows": len(df)}


def _seed_transactions(df: pd.DataFrame, db: Session):
    _log(f"[UPLOAD] Processing {len(df)} rows...")
    # Score with ML
    if ml_service.is_loaded and "is_fraud" in df.columns:
        scored = ml_service.predict_transactions(df)
    else:
        scored = df.copy()
        scored["fraud_probability"] = None
        scored["risk_level"]        = None

    db.query(models.Transaction).delete()
    _log("[UPLOAD] Cleared existing transactions...")

    batch = []
    for _, row in scored.iterrows():
        t = models.Transaction(
            txn_id           = int(row.get("txn_id", 0)),
            farmer_id        = int(row.get("farmer_id", 0)),
            dealer_id        = int(row.get("dealer_id", 0)),
            subsidy_type     = str(row.get("subsidy_type", "")),
            product_type     = str(row.get("product_type", "")),
            quantity         = float(row.get("quantity", 0)),
            subsidy_amount   = float(row.get("subsidy_amount", 0)),
            actual_price     = float(row.get("actual_price", 0)),
            date             = pd.to_datetime(row.get("date"), errors="coerce"),
            season           = str(row.get("season", "")),
            crop_type        = str(row.get("crop_type", "")),
            payment_mode     = str(row.get("payment_mode", "")),
            district         = str(row.get("district", "")),
            land_size_acres  = float(row.get("land_size_acres", 0)),
            distance_farmer_dealer = float(row.get("distance_farmer_dealer", 0)),
            transaction_hour = int(row.get("transaction_hour", 0)),
            day_of_week      = str(row.get("day_of_week", "")),
            transaction_month= int(pd.to_datetime(row.get("date"), errors="coerce").month
                                   if row.get("date") else 0),
            is_fraud         = int(row.get("is_fraud", 0)),
            fraud_type       = str(row.get("fraud_type", "None")),
            fraud_reason     = str(row.get("fraud_reason", "")),
            risk_score       = int(row.get("risk_score", 0)),
            fraud_probability= float(row["fraud_probability"]) if row.get("fraud_probability") is not None else None,
            risk_level       = str(row.get("risk_level", "")) or None,
        )
        batch.append(t)
        if len(batch) >= 500:
            db.bulk_save_objects(batch); db.commit(); batch = []

    if batch:
        db.bulk_save_objects(batch); db.commit()

    _log(f"[UPLOAD] Inserted {len(scored)} transactions.")
    _refresh_dealer_stats(db, scored)
    _log("[UPLOAD] Done!")


def _refresh_dealer_stats(db: Session, df: pd.DataFrame):
    _log("[STATS] Refreshing dealer aggregates...")
    db.query(models.Dealer).update({
        models.Dealer.total_transactions: 0,
        models.Dealer.total_subsidy:      0,
        models.Dealer.farmer_count:       0,
    })

    grp = df.groupby("dealer_id").agg(
        total_transactions=("txn_id",        "count"),
        total_subsidy     =("subsidy_amount", "sum"),
        farmer_count      =("farmer_id",      "nunique"),
        avg_fraud_prob    =("fraud_probability","mean"),
        max_fraud_prob    =("fraud_probability","max"),
    ).reset_index()

    for _, row in grp.iterrows():
        avg_prob = float(row["avg_fraud_prob"]) if not pd.isna(row["avg_fraud_prob"]) else None
        max_prob = float(row["max_fraud_prob"]) if not pd.isna(row["max_fraud_prob"]) else None
        risk     = ("High" if (avg_prob or 0) >= 0.60 else
                    "Medium" if (avg_prob or 0) >= 0.35 else "Low")
        db.query(models.Dealer).filter(
            models.Dealer.dealer_id == int(row["dealer_id"])
        ).update({
            models.Dealer.total_transactions: int(row["total_transactions"]),
            models.Dealer.total_subsidy:      round(float(row["total_subsidy"]), 2),
            models.Dealer.farmer_count:       int(row["farmer_count"]),
            models.Dealer.avg_fraud_prob:     avg_prob,
            models.Dealer.max_fraud_prob:     max_prob,
            models.Dealer.risk_level:         risk,
        })
    db.commit()
    _log("[STATS] Dealer stats refreshed.")


@router.post("/retrain")
def trigger_retrain(background_tasks: BackgroundTasks):
    """Trigger model retraining in background."""
    import subprocess, sys
    def _retrain():
        _log("[RETRAIN] Starting model retraining...")
        r = subprocess.run(
            [sys.executable, "../src/train_xgboost_model.py",
             "--data-dir", str(DATA_DIR),
             "--model-path", str(MODEL_PATH),
             "--n-trials", "30"],
            capture_output=True, text=True, env={**os.environ, "PYTHONUTF8": "1"}
        )
        _log(r.stdout[-2000:] if r.stdout else "No output")
        if r.returncode == 0:
            ml_service.load(MODEL_PATH)
            _log("[RETRAIN] Model reloaded successfully.")
        else:
            _log(f"[RETRAIN] Failed: {r.stderr[-500:]}")
    background_tasks.add_task(_retrain)
    return {"message": "Retraining started in background. Check /api/upload/logs for progress."}
