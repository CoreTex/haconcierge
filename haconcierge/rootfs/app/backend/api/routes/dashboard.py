from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from database.db import get_db
from database.models import Message, Task, Appointment, KeywordHit, Owner

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard_stats(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    total_messages = db.query(func.count(Message.id)).scalar()
    messages_week = db.query(func.count(Message.id)).filter(Message.timestamp >= week_ago).scalar()
    open_tasks = db.query(func.count(Task.id)).filter(Task.status == "open").scalar()
    upcoming_appointments = (
        db.query(func.count(Appointment.id))
        .filter(Appointment.start_time >= now)
        .scalar()
    )
    keyword_hits_week = (
        db.query(func.count(KeywordHit.id))
        .filter(KeywordHit.created_at >= week_ago)
        .scalar()
    )
    active_owners = db.query(func.count(Owner.id)).filter(Owner.active == True).scalar()

    recent_tasks = (
        db.query(Task)
        .order_by(Task.created_at.desc())
        .limit(5)
        .all()
    )
    recent_appts = (
        db.query(Appointment)
        .filter(Appointment.start_time >= now)
        .order_by(Appointment.start_time.asc())
        .limit(5)
        .all()
    )

    return {
        "stats": {
            "total_messages": total_messages,
            "messages_this_week": messages_week,
            "open_tasks": open_tasks,
            "upcoming_appointments": upcoming_appointments,
            "keyword_hits_week": keyword_hits_week,
            "active_owners": active_owners,
        },
        "recent_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "created_at": t.created_at.isoformat(),
            }
            for t in recent_tasks
        ],
        "upcoming_appointments": [
            {
                "id": a.id,
                "title": a.title,
                "start_time": a.start_time.isoformat(),
                "location": a.location,
            }
            for a in recent_appts
        ],
    }
