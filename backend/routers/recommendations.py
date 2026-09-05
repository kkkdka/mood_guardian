
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

import models
from database import get_db
from routers.auth import get_current_user
from schemas import AcceptRequest, FeedbackRequest

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _to_datetime(value: str | None) -> datetime | None:
    
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail="时间格式应为 ISO 格式，如 2026-09-01T19:00:00")


def _get_own_recommendation(db: Session, rec_id: int, user_id: int) -> models.Recommendation:
    
    rec = db.get(models.Recommendation, rec_id)
    if rec is None or rec.user_id != user_id:
        raise HTTPException(status_code=404, detail="推荐记录不存在")
    return rec


def _mark_completed_recommendations(db: Session, user_id: int) -> None:
    
    now = datetime.now()
    recs = db.execute(
        select(models.Recommendation)
        .where(models.Recommendation.user_id == user_id)
        .where(models.Recommendation.status == "accepted")
        .where(models.Recommendation.scheduled_end_time.isnot(None))
        .where(models.Recommendation.scheduled_end_time < now)
    ).scalars().all()
    for rec in recs:
        rec.status = "completed"


def _recommendation_to_dict(rec: models.Recommendation) -> dict:
    

    def _iso(dt: datetime | None) -> str | None:
        return dt.isoformat(timespec="seconds") if dt else None

    return {
        "id": rec.id,
        "user_id": rec.user_id,
        "recommendation_text": rec.recommendation_text,
        "activity_type": rec.activity_type,
        "duration_minutes": rec.duration_minutes,
        "title": rec.title,
        "item_type": rec.item_type,
        "status": rec.status,
        "accepted_at": _iso(rec.accepted_at),
        "scheduled_start_time": _iso(rec.scheduled_start_time),
        "scheduled_end_time": _iso(rec.scheduled_end_time),
        "rating": rec.rating,
        "feedback_text": rec.feedback_text,
        "feedback_at": _iso(rec.feedback_at),
        "created_at": _iso(rec.created_at),
    }


@router.post("/{rec_id}/accept")
def accept_recommendation(
    rec_id: int,
    req: AcceptRequest | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    rec = _get_own_recommendation(db, rec_id, current_user.id)
    if rec.status != "pending":
        raise HTTPException(status_code=409, detail="该推荐已经采纳，不能重复操作")

    
    
    if rec.item_type == "movie" and rec.title:
        movie_exists = db.execute(
            select(models.UserLibrary.id)
            .where(models.UserLibrary.user_id == current_user.id)
            .where(models.UserLibrary.item_type == "movie")
            .where(models.UserLibrary.title == rec.title)
        ).scalar_one_or_none()
        if movie_exists is None:
            db.add(
                models.UserLibrary(
                    user_id=current_user.id,
                    item_type="movie",
                    title=rec.title,
                    status="watched",
                )
            )
    elif rec.item_type == "book" and rec.title:
        reading_exists = db.execute(
            select(models.UserLibrary.id)
            .where(models.UserLibrary.user_id == current_user.id)
            .where(models.UserLibrary.item_type == "book")
            .where(models.UserLibrary.title == rec.title)
            .where(models.UserLibrary.status == "reading")
        ).scalar_one_or_none()
        if reading_exists is None:
            db.add(
                models.UserLibrary(
                    user_id=current_user.id,
                    item_type="book",
                    title=rec.title,
                    status="reading",
                )
            )

    
    rec.status = "accepted"
    rec.accepted_at = datetime.now()
    if req is not None:
        
        rec.scheduled_start_time = _to_datetime(req.scheduled_start_time)
        rec.scheduled_end_time = _to_datetime(req.scheduled_end_time)

    schedule_created = False
    if rec.scheduled_start_time and rec.scheduled_end_time:
        if rec.activity_type == "movie" and rec.title:
            schedule_title = f"看电影《{rec.title}》"
        elif rec.activity_type == "book" and rec.title:
            schedule_title = f"阅读《{rec.title}》"
        elif rec.activity_type == "exercise" and rec.title:
            schedule_title = f"运动：{rec.title}"
        elif rec.activity_type == "relax" and rec.title:
            schedule_title = f"放松：{rec.title}"
        else:
            schedule_title = rec.title or "治愈建议"
        db.add(models.Schedule(
            user_id=current_user.id,
            title=schedule_title,
            start_time=rec.scheduled_start_time,
            end_time=rec.scheduled_end_time,
            completed=False,
            category="life",
        ))
        schedule_created = True

    db.commit()
    return {"message": "已采纳", "schedule_created": schedule_created, "recommendation": _recommendation_to_dict(rec)}


@router.get("/pending_feedback")
def pending_feedback(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    _mark_completed_recommendations(db, current_user.id)
    db.commit()

    recs = db.execute(
        select(models.Recommendation)
        .where(models.Recommendation.user_id == current_user.id)
        .where(models.Recommendation.status == "completed")
        .order_by(desc(models.Recommendation.created_at), desc(models.Recommendation.id))
    ).scalars().all()
    return [_recommendation_to_dict(r) for r in recs]


@router.post("/{rec_id}/feedback")
def submit_feedback(
    rec_id: int,
    req: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    rec = _get_own_recommendation(db, rec_id, current_user.id)
    rec.rating = req.rating
    rec.feedback_text = req.feedback_text
    rec.status = "feedback_given"
    rec.feedback_at = datetime.now()
    db.commit()
    return {"message": "反馈已提交", "recommendation": _recommendation_to_dict(rec)}


@router.get("/history")
def recommendation_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    _mark_completed_recommendations(db, current_user.id)
    db.commit()

    recs = db.execute(
        select(models.Recommendation)
        .where(models.Recommendation.user_id == current_user.id)
        .where(models.Recommendation.status != "pending")
        .order_by(desc(models.Recommendation.created_at), desc(models.Recommendation.id))
    ).scalars().all()
    return [_recommendation_to_dict(r) for r in recs]


@router.delete("/{rec_id}")
def delete_recommendation(
    rec_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    rec = _get_own_recommendation(db, rec_id, current_user.id)

    db.delete(rec)
    db.commit()
    return {"message": "已删除"}