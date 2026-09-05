
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

import models
from database import get_db
from routers import auth
from schemas import EmotionScoreItem, LogRequest, LogUpdateRequest

router = APIRouter(prefix="/api", tags=["logs"])


EMOTION_TAGS = set(models.DEFAULT_EMOTION_TAGS)


def parse_date(s: str):
    
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")


def get_or_create_tag(db: Session, name: str):
    
    tag = db.execute(select(models.Tag).where(models.Tag.name == name)).scalar_one_or_none()
    if tag is None:
        
        category = "emotion" if name in EMOTION_TAGS else "event"
        tag = models.Tag(name=name, category=category)
        db.add(tag)
    return tag


@router.post("/logs")
def create_log(
    req: LogRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    
    log_date = parse_date(req.date)

    
    if not 1 <= req.mood_score <= 10:
        raise HTTPException(status_code=400, detail="心情评分应在 1-10 之间")

    
    log = models.Log(
        user_id=current_user.id,
        date=log_date,
        mood_score=req.mood_score,
        content=req.content,
    )
    db.add(log)
    db.flush()  

    
    log.tags = [get_or_create_tag(db, name) for name in req.tags]

    db.commit()
    db.refresh(log)  

    
    return {
        "id": log.id,
        "user_id": log.user_id,
        "date": str(log.date),
        "mood_score": log.mood_score,
        "content": log.content,
        "tags": req.tags,
    }


def log_to_dict(log: models.Log) -> dict:
    
    return {
        "id": log.id,
        "date": str(log.date),
        "mood_score": log.mood_score,
        "content": log.content,
        "created_at": log.created_at.isoformat(timespec="seconds"),
        "tags": [tag.name for tag in log.tags],          
        "emotion_scores": [                              
            {"emotion_name": es.emotion_name, "score": es.score}
            for es in log.emotion_scores
        ],
    }


@router.get("/logs")
def list_logs(
    start_date: str | None = None,
    end_date: str | None = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    
    
    stmt = select(models.Log).where(models.Log.user_id == current_user.id)

    
    if start_date:
        stmt = stmt.where(models.Log.date >= parse_date(start_date))
    if end_date:
        stmt = stmt.where(models.Log.date <= parse_date(end_date))

    
    stmt = stmt.order_by(desc(models.Log.date), desc(models.Log.id))

    logs = db.execute(stmt).scalars().all()
    return [log_to_dict(log) for log in logs]


@router.put("/logs/{log_id}")
def update_log(
    log_id: int,
    req: LogUpdateRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    
    
    log = db.execute(
        select(models.Log).where(
            models.Log.id == log_id,
            models.Log.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=404, detail="日志不存在")

    
    if req.content is not None:
        log.content = req.content

    
    if req.mood_score is not None:
        if not 1 <= req.mood_score <= 10:
            raise HTTPException(status_code=400, detail="心情评分应在 1-10 之间")
        log.mood_score = req.mood_score

    
    if req.tags is not None:
        log.tags = [get_or_create_tag(db, name) for name in req.tags]

    
    if req.emotion_scores is not None:
        for es in list(log.emotion_scores):
            db.delete(es)
        db.flush()  
        log.emotion_scores = [
            models.EmotionScore(emotion_name=item.emotion_name, score=item.score)
            for item in req.emotion_scores
        ]

    db.commit()
    db.refresh(log)
    return log_to_dict(log)


@router.delete("/logs/{log_id}")
def delete_log(
    log_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    
    
    log = db.execute(
        select(models.Log).where(
            models.Log.id == log_id,
            models.Log.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=404, detail="日志不存在")

    
    for es in list(log.emotion_scores):
        db.delete(es)

    
    log.tags = []

    
    db.delete(log)

    db.commit()
    return {"message": "日志已删除"}