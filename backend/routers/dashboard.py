"""Dashboard KPI and chart endpoints."""
from datetime import datetime
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

DISTRICT_COORDS = {
    "Pune":        (18.5204, 73.8567),
    "Nashik":      (19.9975, 73.7898),
    "Nagpur":      (21.1458, 79.0882),
    "Aurangabad":  (19.8762, 75.3433),
    "Amravati":    (20.9374, 77.7796),
    "Solapur":     (17.6805, 75.9064),
    "Kolhapur":    (16.7050, 74.2433),
    "Jalgaon":     (21.0077, 75.5626),
    "Akola":       (20.7096, 77.0023),
    "Latur":       (18.4088, 76.5604),
}


@router.get("/kpis", response_model=schemas.KPIResponse)
def get_kpis(db: Session = Depends(get_db)):
    total_txns   = db.query(func.count(models.Transaction.id)).scalar() or 0
    total_subsidy= db.query(func.sum(models.Transaction.subsidy_amount)).scalar() or 0.0
    fraud_count  = db.query(func.count(models.Transaction.id)).filter(
        models.Transaction.is_fraud == 1).scalar() or 0
    high_risk    = db.query(func.count(models.Dealer.id)).filter(
        models.Dealer.risk_level == "High").scalar() or 0
    districts    = db.query(func.count(func.distinct(models.Transaction.district))).scalar() or 0
    confirmed    = db.query(func.count(models.Investigation.id)).filter(
        models.Investigation.status == "Confirmed Fraud").scalar() or 0

    return schemas.KPIResponse(
        total_subsidy_distributed=round(float(total_subsidy), 2),
        total_transactions=int(total_txns),
        fraud_percentage=round(fraud_count / max(total_txns, 1) * 100, 2),
        high_risk_dealers=int(high_risk),
        districts_monitored=int(districts),
        confirmed_fraud_cases=int(confirmed),
    )


@router.get("/monthly-trend")
def get_monthly_trend(db: Session = Depends(get_db)):
    txns = db.query(
        models.Transaction.date,
        models.Transaction.is_fraud
    ).all()

    if not txns:
        return []

    rows = [{"date": t.date, "is_fraud": t.is_fraud} for t in txns if t.date]
    df   = pd.DataFrame(rows)
    df["month"] = pd.to_datetime(df["date"]).dt.to_period("M").astype(str)

    grouped = df.groupby("month").agg(
        total_transactions=("is_fraud", "count"),
        fraud_transactions=("is_fraud", "sum"),
    ).reset_index()
    grouped["fraud_rate"] = (grouped["fraud_transactions"] /
                              grouped["total_transactions"] * 100).round(2)
    return grouped.tail(18).to_dict(orient="records")


@router.get("/district-heatmap")
def get_district_heatmap(db: Session = Depends(get_db)):
    txns = db.query(
        models.Transaction.district,
        models.Transaction.is_fraud,
        models.Transaction.fraud_probability,
    ).all()

    if not txns:
        return []

    rows = [{"district": t.district, "is_fraud": t.is_fraud,
             "prob": t.fraud_probability or 0} for t in txns if t.district]
    df   = pd.DataFrame(rows)

    result = []
    for dist, grp in df.groupby("district"):
        coords = DISTRICT_COORDS.get(dist, (20.0, 76.0))
        result.append({
            "district":          dist,
            "lat":               coords[0],
            "lon":               coords[1],
            "total_transactions":int(len(grp)),
            "fraud_count":       int(grp["is_fraud"].sum()),
            "fraud_rate":        round(grp["is_fraud"].mean() * 100, 2),
            "avg_fraud_prob":    round(float(grp["prob"].mean()), 4),
        })
    return result


@router.get("/fraud-type-breakdown")
def get_fraud_type_breakdown(db: Session = Depends(get_db)):
    txns = db.query(
        models.Transaction.fraud_type,
        func.count(models.Transaction.id).label("count")
    ).filter(models.Transaction.is_fraud == 1).group_by(
        models.Transaction.fraud_type).all()
    return [{"fraud_type": t.fraud_type or "Unknown", "count": t.count}
            for t in txns]
