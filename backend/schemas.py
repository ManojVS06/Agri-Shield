"""Pydantic schemas for API request/response validation."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class KPIResponse(BaseModel):
    total_subsidy_distributed: float
    total_transactions: int
    fraud_percentage: float
    high_risk_dealers: int
    districts_monitored: int
    confirmed_fraud_cases: int


class MonthlyTrend(BaseModel):
    month: str
    total_transactions: int
    fraud_transactions: int
    fraud_rate: float


class DistrictHeatmap(BaseModel):
    district: str
    lat: float
    lon: float
    total_transactions: int
    fraud_count: int
    fraud_rate: float
    avg_fraud_prob: float


# ---------------------------------------------------------------------------
# Dealers
# ---------------------------------------------------------------------------

class DealerSummary(BaseModel):
    dealer_id: int
    dealer_name: str
    district: str
    farmer_count: int
    total_transactions: int
    total_subsidy: float
    avg_fraud_prob: Optional[float]
    rule_score: Optional[float]
    risk_level: Optional[str]

    class Config:
        from_attributes = True


class DealerDetail(DealerSummary):
    shop_size: str
    years_active: int
    avg_daily_sales: float
    max_fraud_prob: Optional[float]
    dealer_location_lat: Optional[float]
    dealer_location_long: Optional[float]
    insights: list[str] = []

    class Config:
        from_attributes = True


class DealerSearchResult(BaseModel):
    dealer_id: int
    dealer_name: str
    district: str
    risk_level: Optional[str]


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

class TransactionOut(BaseModel):
    txn_id: int
    farmer_id: int
    dealer_id: int
    subsidy_type: str
    product_type: str
    quantity: float
    subsidy_amount: float
    actual_price: float
    date: Optional[datetime]
    season: Optional[str]
    district: Optional[str]
    land_size_acres: Optional[float]
    payment_mode: Optional[str]
    distance_farmer_dealer: Optional[float]
    is_fraud: int
    fraud_type: Optional[str]
    risk_score: Optional[int]
    fraud_probability: Optional[float]
    rule_score: Optional[float]
    risk_level: Optional[str]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Investigations
# ---------------------------------------------------------------------------

class InvestigationUpdate(BaseModel):
    dealer_id: int
    txn_id: Optional[int] = None
    status: str  # Pending / Under Review / Confirmed Fraud / Cleared
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None


class InvestigationOut(BaseModel):
    id: int
    dealer_id: int
    txn_id: Optional[int]
    status: str
    assigned_to: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class AlertOut(BaseModel):
    dealer_id: int
    dealer_name: str
    district: str
    avg_fraud_prob: float
    rule_score: Optional[float]
    risk_level: str
    farmer_count: int
    total_transactions: int
    investigation_status: Optional[str]
