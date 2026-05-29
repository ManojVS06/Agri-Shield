"""Transaction endpoints."""
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from ml_service import ml_service

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=list[schemas.TransactionOut])
def list_transactions(
    dealer_id:  Optional[int]   = None,
    farmer_id:  Optional[int]   = None,
    district:   Optional[str]   = None,
    is_fraud:   Optional[int]   = None,
    risk_level: Optional[str]   = None,
    skip:  int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(models.Transaction)
    if dealer_id  is not None: query = query.filter(models.Transaction.dealer_id  == dealer_id)
    if farmer_id  is not None: query = query.filter(models.Transaction.farmer_id  == farmer_id)
    if district:               query = query.filter(models.Transaction.district   == district)
    if is_fraud   is not None: query = query.filter(models.Transaction.is_fraud   == is_fraud)
    if risk_level:             query = query.filter(models.Transaction.risk_level == risk_level)

    return (query
            .order_by(models.Transaction.fraud_probability.desc().nullslast())
            .offset(skip).limit(limit).all())


@router.get("/{txn_id}", response_model=schemas.TransactionOut)
def get_transaction(txn_id: int, db: Session = Depends(get_db)):
    txn = db.query(models.Transaction).filter(
        models.Transaction.txn_id == txn_id).first()
    if not txn:
        from fastapi import HTTPException
        raise HTTPException(404, f"Transaction {txn_id} not found")
    return txn


@router.get("/high-risk/list")
def get_high_risk_transactions(
    threshold: float = Query(0.70),
    limit: int = Query(200),
    db: Session = Depends(get_db),
):
    txns = (db.query(models.Transaction)
            .filter(models.Transaction.fraud_probability >= threshold)
            .order_by(models.Transaction.fraud_probability.desc())
            .limit(limit).all())
    return [schemas.TransactionOut.model_validate(t) for t in txns]


@router.get("/{txn_id}/shap")
def get_shap_explanation(txn_id: int, db: Session = Depends(get_db)):
    """Return top-5 SHAP feature contributions for a single transaction."""
    txn = db.query(models.Transaction).filter(
        models.Transaction.txn_id == txn_id).first()
    if not txn:
        raise HTTPException(404, f"Transaction {txn_id} not found")

    if not ml_service.is_loaded:
        return {"shap_values": [], "message": "Model not loaded — SHAP unavailable"}

    # Build a row dict from the ORM object
    row = {
        "txn_id":                txn.txn_id,
        "farmer_id":             txn.farmer_id,
        "dealer_id":             txn.dealer_id,
        "subsidy_type":          txn.subsidy_type or "",
        "product_type":          txn.product_type or "",
        "quantity":              txn.quantity or 0,
        "subsidy_amount":        txn.subsidy_amount or 0,
        "actual_price":          txn.actual_price or 0,
        "date":                  txn.date,
        "season":                txn.season or "",
        "crop_type":             txn.crop_type or "",
        "payment_mode":          txn.payment_mode or "",
        "district":              txn.district or "",
        "land_size_acres":       txn.land_size_acres or 0,
        "distance_farmer_dealer":txn.distance_farmer_dealer or 0,
        "transaction_hour":      txn.transaction_hour or 0,
        "day_of_week":           txn.day_of_week or "",
        "is_fraud":              txn.is_fraud or 0,
        "risk_score":            txn.risk_score or 0,
    }
    df = pd.DataFrame([row])
    explanations = ml_service.get_shap_explanations(df, max_rows=1)
    shap_values  = explanations[0] if explanations else []

    return {
        "txn_id":          txn_id,
        "fraud_probability":txn.fraud_probability,
        "risk_level":      txn.risk_level,
        "shap_values":     shap_values,
    }
