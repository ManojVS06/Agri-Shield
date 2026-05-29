"""Investigation and audit log endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


@router.get("", response_model=list[schemas.InvestigationOut])
def list_investigations(
    dealer_id: int | None = None,
    status:    str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Investigation)
    if dealer_id: query = query.filter(models.Investigation.dealer_id == dealer_id)
    if status:    query = query.filter(models.Investigation.status    == status)
    return query.order_by(models.Investigation.updated_at.desc()).limit(500).all()


@router.post("/update", response_model=schemas.InvestigationOut)
def update_investigation(body: schemas.InvestigationUpdate, db: Session = Depends(get_db)):
    # Upsert: find existing open investigation for dealer or create new
    inv = (db.query(models.Investigation)
           .filter(models.Investigation.dealer_id == body.dealer_id,
                   models.Investigation.status.notin_(["Confirmed Fraud", "Cleared"]))
           .first())

    if inv:
        inv.status      = body.status
        inv.assigned_to = body.assigned_to or inv.assigned_to
        inv.notes       = body.notes or inv.notes
        inv.updated_at  = datetime.utcnow()
    else:
        inv = models.Investigation(
            dealer_id   = body.dealer_id,
            txn_id      = body.txn_id,
            status      = body.status,
            assigned_to = body.assigned_to,
            notes       = body.notes,
            created_by  = body.user_email,
            created_at  = datetime.utcnow(),
            updated_at  = datetime.utcnow(),
        )
        db.add(inv)

    # Write audit log
    log = models.AuditLog(
        user_id     = body.user_id or "anonymous",
        user_email  = body.user_email or "unknown",
        action      = f"Updated investigation status to '{body.status}'",
        entity_type = "investigation",
        entity_id   = body.dealer_id,
        details     = {"notes": body.notes, "assigned_to": body.assigned_to},
        timestamp   = datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(inv)
    return inv


@router.get("/alerts/high-risk")
def get_high_risk_alerts(threshold: float = 0.65, db: Session = Depends(get_db)):
    dealers = (db.query(models.Dealer)
               .filter(models.Dealer.avg_fraud_prob >= threshold)
               .order_by(models.Dealer.avg_fraud_prob.desc())
               .limit(100).all())

    results = []
    for d in dealers:
        inv = (db.query(models.Investigation)
               .filter(models.Investigation.dealer_id == d.dealer_id)
               .order_by(models.Investigation.updated_at.desc())
               .first())
        results.append(schemas.AlertOut(
            dealer_id              = d.dealer_id,
            dealer_name            = d.dealer_name,
            district               = d.district,
            avg_fraud_prob         = d.avg_fraud_prob or 0,
            rule_score             = d.rule_score,
            risk_level             = d.risk_level or "High",
            farmer_count           = d.farmer_count or 0,
            total_transactions     = d.total_transactions or 0,
            investigation_status   = inv.status if inv else None,
        ))
    return results


@router.get("/logs")
def get_audit_logs(limit: int = 200, db: Session = Depends(get_db)):
    logs = (db.query(models.AuditLog)
            .order_by(models.AuditLog.timestamp.desc())
            .limit(limit).all())
    return [{
        "id":          l.id,
        "user_email":  l.user_email,
        "action":      l.action,
        "entity_type": l.entity_type,
        "entity_id":   l.entity_id,
        "details":     l.details,
        "timestamp":   l.timestamp.isoformat() if l.timestamp else None,
    } for l in logs]
