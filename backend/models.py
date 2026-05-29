"""SQLAlchemy ORM models for the fraud detection platform."""
from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Float, Integer, String,
                         Text, ForeignKey, JSON)
from sqlalchemy.orm import relationship

from database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id               = Column(Integer, primary_key=True, index=True)
    txn_id           = Column(Integer, unique=True, index=True)
    farmer_id        = Column(Integer, index=True)
    dealer_id        = Column(Integer, index=True)
    subsidy_type     = Column(String(50))
    product_type     = Column(String(100))
    quantity         = Column(Float)
    subsidy_amount   = Column(Float)
    actual_price     = Column(Float)
    date             = Column(DateTime)
    season           = Column(String(20))
    crop_type        = Column(String(50))
    payment_mode     = Column(String(20))
    district         = Column(String(100))
    land_size_acres  = Column(Float)
    distance_farmer_dealer = Column(Float)
    transaction_hour = Column(Integer)
    day_of_week      = Column(String(20))
    transaction_month= Column(Integer)
    is_fraud         = Column(Integer, default=0)
    fraud_type       = Column(String(100))
    fraud_reason     = Column(Text)
    risk_score       = Column(Integer)
    # ML predictions (populated after scoring)
    fraud_probability= Column(Float, nullable=True)
    rule_score       = Column(Float, nullable=True)
    combined_score   = Column(Float, nullable=True)
    risk_level       = Column(String(20), nullable=True)  # High/Medium/Low
    scored_at        = Column(DateTime, nullable=True)


class Dealer(Base):
    __tablename__ = "dealers"

    id               = Column(Integer, primary_key=True, index=True)
    dealer_id        = Column(Integer, unique=True, index=True)
    dealer_name      = Column(String(200))
    district         = Column(String(100))
    license_number   = Column(String(100))
    shop_size        = Column(String(20))
    years_active     = Column(Integer)
    gst_number       = Column(String(50))
    avg_daily_sales  = Column(Float)
    dealer_location_lat  = Column(Float)
    dealer_location_long = Column(Float)
    # Computed stats (refreshed on scoring)
    total_transactions   = Column(Integer, default=0)
    total_subsidy        = Column(Float, default=0.0)
    farmer_count         = Column(Integer, default=0)
    avg_fraud_prob       = Column(Float, nullable=True)
    max_fraud_prob       = Column(Float, nullable=True)
    rule_score           = Column(Float, nullable=True)
    risk_level           = Column(String(20), nullable=True)


class Farmer(Base):
    __tablename__ = "farmers"

    id               = Column(Integer, primary_key=True, index=True)
    farmer_id        = Column(Integer, unique=True, index=True)
    name             = Column(String(200))
    district         = Column(String(100))
    village          = Column(String(100))
    land_size_acres  = Column(Float)
    crop_type        = Column(String(50))
    income_category  = Column(String(50))
    farmer_location_lat  = Column(Float)
    farmer_location_long = Column(Float)


class Investigation(Base):
    __tablename__ = "investigations"

    id          = Column(Integer, primary_key=True, index=True)
    dealer_id   = Column(Integer, index=True)
    txn_id      = Column(Integer, nullable=True)
    status      = Column(String(50), default="Pending")  # Pending/Under Review/Confirmed Fraud/Cleared
    assigned_to = Column(String(200), nullable=True)
    notes       = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by  = Column(String(200), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(String(200))
    user_email  = Column(String(200))
    action      = Column(String(200))
    entity_type = Column(String(50))   # dealer / transaction / investigation
    entity_id   = Column(Integer)
    details     = Column(JSON, nullable=True)
    timestamp   = Column(DateTime, default=datetime.utcnow)
