"""Farmers router — list and detail endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

import models
from database import get_db

router = APIRouter(prefix="/api/farmers", tags=["farmers"])


@router.get("")
def list_farmers(
    district:       Optional[str] = None,
    crop_type:      Optional[str] = None,
    income_category:Optional[str] = None,
    skip:  int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
):
    """List farmers with optional filters."""
    query = db.query(models.Farmer)
    if district:        query = query.filter(models.Farmer.district        == district)
    if crop_type:       query = query.filter(models.Farmer.crop_type       == crop_type)
    if income_category: query = query.filter(models.Farmer.income_category == income_category)
    farmers = query.offset(skip).limit(limit).all()
    return [
        {
            "farmer_id":         f.farmer_id,
            "name":              f.name,
            "district":          f.district,
            "village":           f.village,
            "land_size_acres":   f.land_size_acres,
            "crop_type":         f.crop_type,
            "income_category":   f.income_category,
            "farmer_location_lat":  f.farmer_location_lat,
            "farmer_location_long": f.farmer_location_long,
        }
        for f in farmers
    ]


@router.get("/districts")
def farmer_districts(db: Session = Depends(get_db)):
    """Return distinct districts for filter dropdowns."""
    rows = db.query(models.Farmer.district).distinct().all()
    return sorted([r[0] for r in rows if r[0]])


@router.get("/crops")
def farmer_crops(db: Session = Depends(get_db)):
    """Return distinct crop types for filter dropdowns."""
    rows = db.query(models.Farmer.crop_type).distinct().all()
    return sorted([r[0] for r in rows if r[0]])


@router.get("/{farmer_id}")
def get_farmer(farmer_id: int, db: Session = Depends(get_db)):
    """Full farmer profile with their transaction history."""
    farmer = db.query(models.Farmer).filter(models.Farmer.farmer_id == farmer_id).first()
    if not farmer:
        raise HTTPException(404, f"Farmer {farmer_id} not found")

    txns = (
        db.query(models.Transaction)
        .filter(models.Transaction.farmer_id == farmer_id)
        .order_by(models.Transaction.fraud_probability.desc().nullslast())
        .limit(50)
        .all()
    )

    total_subsidy = sum(t.subsidy_amount or 0 for t in txns)
    fraud_count   = sum(1 for t in txns if t.is_fraud)
    avg_prob      = (sum(t.fraud_probability or 0 for t in txns) / max(len(txns), 1))

    return {
        "farmer_id":            farmer.farmer_id,
        "name":                 farmer.name,
        "district":             farmer.district,
        "village":              farmer.village,
        "land_size_acres":      farmer.land_size_acres,
        "crop_type":            farmer.crop_type,
        "income_category":      farmer.income_category,
        "farmer_location_lat":  farmer.farmer_location_lat,
        "farmer_location_long": farmer.farmer_location_long,
        "stats": {
            "total_transactions": len(txns),
            "total_subsidy":      round(total_subsidy, 2),
            "fraud_count":        fraud_count,
            "avg_fraud_prob":     round(avg_prob, 4),
        },
        "recent_transactions": [
            {
                "txn_id":           t.txn_id,
                "dealer_id":        t.dealer_id,
                "subsidy_type":     t.subsidy_type,
                "subsidy_amount":   t.subsidy_amount,
                "date":             t.date.isoformat() if t.date else None,
                "fraud_probability":t.fraud_probability,
                "risk_level":       t.risk_level,
                "is_fraud":         t.is_fraud,
            }
            for t in txns[:20]
        ],
    }
