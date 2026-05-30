"""Dealer endpoints — list, search, profile."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from fraud_rules import generate_dealer_insights
from ml_service import ml_service

router = APIRouter(prefix="/api/dealers", tags=["dealers"])


@router.get("/search")
def search_dealers(
    q: str = Query("", min_length=0),
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
):
    """Autocomplete dealer search by name, ID, or district."""
    query = db.query(models.Dealer)
    if q:
        query = query.filter(
            or_(
                models.Dealer.dealer_name.ilike(f"%{q}%"),
                models.Dealer.district.ilike(f"%{q}%"),
                models.Dealer.dealer_id == (int(q) if q.isdigit() else -1),
            )
        )
    dealers = query.limit(limit).all()
    return [{"dealer_id": d.dealer_id, "dealer_name": d.dealer_name,
             "district": d.district, "risk_level": d.risk_level}
            for d in dealers]


@router.get("", response_model=list[schemas.DealerSummary])
def list_dealers(
    district:   Optional[str] = None,
    risk_level: Optional[str] = None,
    skip:  int = Query(0, ge=0),
    limit: int = Query(50, le=500),
    sort_by: str = Query("avg_fraud_prob"),
    db: Session = Depends(get_db),
):
    query = db.query(models.Dealer)
    if district:
        query = query.filter(models.Dealer.district == district)
    if risk_level:
        query = query.filter(models.Dealer.risk_level == risk_level)

    if sort_by == "avg_fraud_prob":
        query = query.order_by(models.Dealer.avg_fraud_prob.desc().nullslast())
    elif sort_by == "total_subsidy":
        query = query.order_by(models.Dealer.total_subsidy.desc().nullslast())
    elif sort_by == "farmer_count":
        query = query.order_by(models.Dealer.farmer_count.desc().nullslast())

    return query.offset(skip).limit(limit).all()


@router.get("/{dealer_id}", response_model=schemas.DealerDetail)
def get_dealer(dealer_id: int, db: Session = Depends(get_db)):
    dealer = db.query(models.Dealer).filter(
        models.Dealer.dealer_id == dealer_id).first()
    if not dealer:
        from fastapi import HTTPException
        raise HTTPException(404, f"Dealer {dealer_id} not found")

    insights = generate_dealer_insights(dealer_id, db)
    result   = schemas.DealerDetail.model_validate(dealer)
    result.insights = insights
    return result


@router.get("/{dealer_id}/stats")
def get_dealer_stats(dealer_id: int, db: Session = Depends(get_db)):
    """Return dealer stats vs district averages for the profile comparison chart."""
    dealer = db.query(models.Dealer).filter(
        models.Dealer.dealer_id == dealer_id).first()
    if not dealer:
        return {}

    txns = db.query(models.Transaction).filter(
        models.Transaction.dealer_id == dealer_id).all()
    dist_txns = db.query(models.Transaction).filter(
        models.Transaction.district == dealer.district).all()

    dist_dealers = set(t.dealer_id for t in dist_txns)
    n_dist       = max(len(dist_dealers), 1)

    return {
        "dealer_id":           dealer_id,
        "dealer_txn_count":    len(txns),
        "district_avg_txns":   round(len(dist_txns) / n_dist, 1),
        "dealer_avg_subsidy":  round(sum(t.subsidy_amount or 0 for t in txns) / max(len(txns),1), 2),
        "district_avg_subsidy":round(sum(t.subsidy_amount or 0 for t in dist_txns) / max(len(dist_txns),1), 2),
        "dealer_farmer_count": len(set(t.farmer_id for t in txns)),
        "district_avg_farmers":round(len(set(t.farmer_id for t in dist_txns)) / n_dist, 1),
        "dealer_fraud_rate":   round(sum(t.is_fraud for t in txns) / max(len(txns),1) * 100, 2),
        "district_fraud_rate": round(sum(t.is_fraud for t in dist_txns) / max(len(dist_txns),1) * 100, 2),
    }


@router.get("/{dealer_id}/map-data")
def get_dealer_map_data(dealer_id: int, db: Session = Depends(get_db)):
    dealer = db.query(models.Dealer).filter(models.Dealer.dealer_id == dealer_id).first()
    if not dealer:
        from fastapi import HTTPException
        raise HTTPException(404, f"Dealer {dealer_id} not found")

    # Join transactions and farmers to extract unique coordinates
    results = (
        db.query(
            models.Farmer.farmer_id,
            models.Farmer.name,
            models.Farmer.farmer_location_lat,
            models.Farmer.farmer_location_long,
            func.count(models.Transaction.id).label("txn_count"),
            func.max(models.Transaction.fraud_probability).label("max_fraud_prob")
        )
        .join(models.Transaction, models.Transaction.farmer_id == models.Farmer.farmer_id)
        .filter(models.Transaction.dealer_id == dealer_id)
        .group_by(
            models.Farmer.farmer_id,
            models.Farmer.name,
            models.Farmer.farmer_location_lat,
            models.Farmer.farmer_location_long
        )
        .all()
    )

    farmers_list = []
    for r in results:
        prob = float(r.max_fraud_prob) if r.max_fraud_prob is not None else 0.0
        risk = "High" if prob >= 0.6 else "Medium" if prob >= 0.35 else "Low"
        farmers_list.append({
            "farmer_id": r.farmer_id,
            "name": r.name,
            "lat": float(r.farmer_location_lat) if r.farmer_location_lat else None,
            "long": float(r.farmer_location_long) if r.farmer_location_long else None,
            "txn_count": r.txn_count,
            "risk_level": risk,
            "max_fraud_prob": prob
        })

    return {
        "dealer_id": dealer.dealer_id,
        "dealer_name": dealer.dealer_name,
        "lat": float(dealer.dealer_location_lat) if dealer.dealer_location_lat else None,
        "long": float(dealer.dealer_location_long) if dealer.dealer_location_long else None,
        "farmers": farmers_list
    }
