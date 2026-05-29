"""Rule-based SQL/pandas anomaly scoring engine.

Computes a 0-100 anomaly score by evaluating 6 fraud rules
against transaction data. Complements the ML model score.
"""
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
import models


RULES = {
    "ghost_farmer":    25,  # max points per rule
    "price_anomaly":   20,
    "high_volume":     20,
    "rapid_retransact":15,
    "long_distance":   10,
    "over_claiming":   10,
}
TOTAL_POSSIBLE = sum(RULES.values())  # 100


def compute_rule_score(txn: models.Transaction, district_stats: dict) -> float:
    """Score a single transaction against all rules. Returns 0-100."""
    score = 0.0

    # Rule 1: Ghost Farmer (land size near zero)
    if txn.land_size_acres is not None and txn.land_size_acres < 0.1:
        score += RULES["ghost_farmer"]
    elif txn.land_size_acres is not None and txn.land_size_acres < 0.3:
        score += RULES["ghost_farmer"] * 0.5

    # Rule 2: Price anomaly (actual_price very low vs subsidy)
    if txn.actual_price is not None and txn.subsidy_amount:
        ratio = txn.actual_price / (txn.subsidy_amount + 1e-6)
        if ratio < 0.05:
            score += RULES["price_anomaly"]
        elif ratio < 0.20:
            score += RULES["price_anomaly"] * 0.6

    # Rule 3: High dealer volume vs district average
    dist_avg = district_stats.get(txn.district, {}).get("avg_dealer_farmers", 20)
    # dealer_farmers_count not stored per txn, approximate via district stats
    dealer_txns = district_stats.get(txn.district, {}).get(
        "dealer_txn_counts", {}).get(txn.dealer_id, 0)
    if dealer_txns > dist_avg * 2.5:
        score += RULES["high_volume"]
    elif dealer_txns > dist_avg * 1.5:
        score += RULES["high_volume"] * 0.5

    # Rule 4: Rapid re-transaction (days_since_last_txn very small)
    # We don't have this per-txn in DB easily; use transaction_hour as proxy
    if txn.transaction_hour is not None:
        if txn.transaction_hour < 6 or txn.transaction_hour > 20:
            score += RULES["rapid_retransact"] * 0.7

    # Rule 5: Unusual distance
    if txn.distance_farmer_dealer is not None:
        if txn.distance_farmer_dealer > 500:
            score += RULES["long_distance"]
        elif txn.distance_farmer_dealer > 300:
            score += RULES["long_distance"] * 0.5

    # Rule 6: Over-claiming (subsidy_amount per acre very high)
    if txn.land_size_acres and txn.land_size_acres > 0.1:
        spa = txn.subsidy_amount / txn.land_size_acres
        dist_mean_spa = district_stats.get(txn.district, {}).get("mean_spa", 300)
        if spa > dist_mean_spa * 2.5:
            score += RULES["over_claiming"]
        elif spa > dist_mean_spa * 1.8:
            score += RULES["over_claiming"] * 0.5

    return round(min(score / TOTAL_POSSIBLE * 100, 100), 2)


def build_district_stats(db: Session) -> dict:
    """Pre-compute district-level statistics for rule evaluation."""
    txns = db.query(models.Transaction).all()
    if not txns:
        return {}

    rows = [{
        "district":     t.district or "Unknown",
        "dealer_id":    t.dealer_id,
        "subsidy_amount":t.subsidy_amount or 0,
        "land_size_acres":t.land_size_acres or 0,
    } for t in txns]
    df = pd.DataFrame(rows)

    stats = {}
    for dist, grp in df.groupby("district"):
        dealer_counts = grp.groupby("dealer_id").size().to_dict()
        valid = grp[grp["land_size_acres"] > 0.1]
        mean_spa = float((valid["subsidy_amount"] / valid["land_size_acres"]).mean()) if len(valid) else 300.0
        stats[dist] = {
            "avg_dealer_farmers":  float(grp.groupby("dealer_id").size().mean()),
            "dealer_txn_counts":   dealer_counts,
            "mean_spa":            mean_spa,
        }
    return stats


def score_all_transactions(db: Session) -> None:
    """Batch-score all transactions in DB and update rule_score column."""
    district_stats = build_district_stats(db)
    txns = db.query(models.Transaction).all()
    for txn in txns:
        txn.rule_score = compute_rule_score(txn, district_stats)
    db.commit()


def generate_dealer_insights(dealer_id: int, db: Session) -> list[str]:
    """Generate human-readable insight sentences for a dealer profile."""
    from sqlalchemy import func

    dealer = db.query(models.Dealer).filter(models.Dealer.dealer_id == dealer_id).first()
    if not dealer:
        return []

    txns = db.query(models.Transaction).filter(
        models.Transaction.dealer_id == dealer_id).all()
    if not txns:
        return []

    insights = []
    n = len(txns)
    avg_subsidy = sum(t.subsidy_amount or 0 for t in txns) / max(n, 1)
    farmer_ids  = set(t.farmer_id for t in txns)

    # Compare to district average
    dist_txns   = db.query(models.Transaction).filter(
        models.Transaction.district == dealer.district).all()
    dist_dealers = set(t.dealer_id for t in dist_txns)
    if dist_dealers:
        dist_avg_txns = len(dist_txns) / len(dist_dealers)
        ratio = n / max(dist_avg_txns, 1)
        if ratio > 2.0:
            insights.append(
                f"Dealer handles {ratio:.1f}x more transactions than the district average.")

    dist_avg_subsidy = (sum(t.subsidy_amount or 0 for t in dist_txns) /
                        max(len(dist_txns), 1))
    if avg_subsidy > dist_avg_subsidy * 1.6:
        insights.append(
            f"Average subsidy amount (Rs {avg_subsidy:,.0f}) is "
            f"{avg_subsidy/dist_avg_subsidy:.1f}x the district average.")

    zero_land = sum(1 for t in txns if (t.land_size_acres or 1) < 0.1)
    if zero_land > 0:
        insights.append(
            f"{zero_land} transaction(s) have near-zero land size (potential ghost farmers).")

    fake_price = sum(1 for t in txns if (t.actual_price or 1) < 10)
    if fake_price > 0:
        insights.append(
            f"{fake_price} transaction(s) have near-zero actual price (potential fake sales).")

    high_prob = [t for t in txns if (t.fraud_probability or 0) > 0.7]
    if high_prob:
        insights.append(
            f"{len(high_prob)} transaction(s) flagged as high-risk by ML model (>70% probability).")

    if not insights:
        insights.append("No significant anomalies detected. Risk appears within normal range.")

    return insights
