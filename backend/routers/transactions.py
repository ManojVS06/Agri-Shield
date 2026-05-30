"""Transaction endpoints."""
import os
from typing import Optional

import httpx
import pandas as pd
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func
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


@router.get("/{txn_id}/explanation")
async def get_transaction_explanation(txn_id: int, db: Session = Depends(get_db)):
    """Generate a semantic description of transaction fraud using Gemini."""
    # 1. Fetch transaction
    txn = db.query(models.Transaction).filter(
        models.Transaction.txn_id == txn_id).first()
    if not txn:
        raise HTTPException(404, f"Transaction {txn_id} not found")

    # 2. Fetch farmer info if available
    farmer_name = "Unknown Farmer"
    farmer = db.query(models.Farmer).filter(
        models.Farmer.farmer_id == txn.farmer_id).first()
    if farmer:
        farmer_name = farmer.name

    # 3. Calculate context-specific stats
    farmer_avg_qty = db.query(func.avg(models.Transaction.quantity)).filter(
        models.Transaction.farmer_id == txn.farmer_id
    ).scalar() or 0.0

    district_avg_qty = db.query(func.avg(models.Transaction.quantity)).filter(
        models.Transaction.district == txn.district
    ).scalar() or 0.0

    # District average subsidy per acre
    district_avg_spa = db.query(func.avg(models.Transaction.subsidy_amount / models.Transaction.land_size_acres)).filter(
        models.Transaction.district == txn.district,
        models.Transaction.land_size_acres > 0.1
    ).scalar() or 300.0

    # District average farmer-dealer distance
    district_avg_dist = db.query(func.avg(models.Transaction.distance_farmer_dealer)).filter(
        models.Transaction.district == txn.district
    ).scalar() or 15.0

    # Current subsidy per acre
    subsidy_per_acre = 0.0
    if txn.land_size_acres and txn.land_size_acres > 0:
        subsidy_per_acre = txn.subsidy_amount / txn.land_size_acres

    # 4. Check if Gemini API key is configured
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()

    if not gemini_key:
        return {
            "explanation": "Gemini API key is missing. Please add GEMINI_API_KEY to your backend/.env file to enable automated AI fraud reasoning."
        }

    # Clean up potentially null or nan string values from dataset
    fraud_type = txn.fraud_type
    if not fraud_type or str(fraud_type).lower() in ("nan", "none", "null"):
        fraud_type = "General Anomaly"

    fraud_reason = txn.fraud_reason
    if not fraud_reason or str(fraud_reason).lower() in ("nan", "none", "null"):
        fraud_reason = "high statistical anomaly and probability mismatch"

    # 5. Formulate structured prompt
    prompt = f"""
You are an agricultural subsidy fraud investigator auditing a flagged transaction.
Analyze this transaction's features and explain why it was flagged under the rule: '{fraud_type}' (reason: {fraud_reason}).
Provide a clear, natural explanation in exactly 2-3 concise sentences using the statistics and facts below. Be professional, objective, and direct. Do not mention math formulas or coding terms; focus on the agricultural realism (e.g. over-claiming quantities, ghost farmer land sizes, unusual travel distances).

Transaction details:
- Farmer Name: {farmer_name}
- Crop Type: {txn.crop_type or 'Unknown'}
- Land Size: {txn.land_size_acres or 0} acres
- Subsidized Product: {txn.product_type or 'fertilizer/seeds'} ({txn.subsidy_type or 'General'})
- Current Transaction Quantity: {txn.quantity or 0} bags/units
- Farmer's Historical Average Quantity: {farmer_avg_qty:.2f} bags/units
- District Average Quantity: {district_avg_qty:.2f} bags/units
- Current Subsidy Amount: Rs {txn.subsidy_amount or 0:,.2f} (Rs {subsidy_per_acre:,.2f} per acre)
- District Average Subsidy per Acre: Rs {district_avg_spa:,.2f}
- Distance between Farmer & Dealer: {txn.distance_farmer_dealer or 0} km (District average distance: {district_avg_dist:.2f} km)
- Transaction Hour: {txn.transaction_hour or 12}:00
- Risk Score: {txn.risk_score or 0} (Scale 0-100, where typical values are 5-45)
- Anomaly Flag: {txn.fraud_type or 'Suspicious Anomaly'} ({txn.fraud_reason or 'deviates from historical patterns'})
"""

    # 6. Make request to Gemini
    # API URL: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 400,
            "thinkingConfig": {
                "thinkingBudget": 0
            }
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=20.0)
            if response.status_code != 200:
                return {
                    "explanation": f"Gemini API returned an error (status {response.status_code}): {response.text}"
                }
            
            data = response.json()
            try:
                explanation = data['candidates'][0]['content']['parts'][0]['text'].strip()
                return {"explanation": explanation}
            except (KeyError, IndexError) as parse_err:
                return {
                    "explanation": f"Failed to parse Gemini API response structure. Response: {data}"
                }
    except Exception as e:
        return {
            "explanation": f"Failed to query Gemini API: {str(e)}"
        }

