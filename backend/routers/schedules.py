
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

import models
from database import get_db
from routers import auth
from schemas import ScheduleRequest

router = APIRouter(prefix="/api", tags=["schedules"])


def parse_day(s: str) -> datetime:
    
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")


def get_owned_schedule(
    db: Session, sched_id: int, current_user: models.User
) -> models.Schedule:
    
    sched = db.execute(
        select(models.Schedule).where(
            models.Schedule.id == sched_id,
            models.Schedule.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if sched is None:
        raise HTTPException(status_code=404, detail="日程不存在")
    return sched


def schedule_to_dict(s: models.Schedule) -> dict:
    
    return {
        "id": s.id,
        "user_id": s.user_id,
        "title": s.title,
        "start_time": s.start_time.strftime("%Y-%m-%dT%H:%M"),
        "end_time": s.end_time.strftime("%Y-%m-%dT%H:%M"),
        "completed": s.completed,
        "category": s.category,
    }


@router.get("/schedules")
def list_schedules(
    start_date: str | None = None,  
    end_date: str | None = None,    
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    
    stmt = select(models.Schedule).where(models.Schedule.user_id == current_user.id)
    if start_date:
        
        stmt = stmt.where(models.Schedule.start_time >= parse_day(start_date))
    if end_date:
        
        stmt = stmt.where(models.Schedule.start_time < parse_day(end_date) + timedelta(days=1))
    stmt = stmt.order_by(models.Schedule.start_time.asc())

    schedules = db.execute(stmt).scalars().all()
    return [schedule_to_dict(s) for s in schedules]


@router.post("/schedules")
def create_schedule(
    req: ScheduleRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    
    if req.start_time >= req.end_time:
        raise HTTPException(status_code=400, detail="结束时间应晚于开始时间")

    sched = models.Schedule(
        user_id=current_user.id,
        title=req.title,
        start_time=req.start_time,
        end_time=req.end_time,
        completed=req.completed,
        category=req.category,
    )
    db.add(sched)
    db.commit()
    db.refresh(sched)  

    return schedule_to_dict(sched)


@router.put("/schedules/{sched_id}")
def update_schedule(
    sched_id: int,
    req: ScheduleRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    
    sched = get_owned_schedule(db, sched_id, current_user)

    if req.start_time >= req.end_time:
        raise HTTPException(status_code=400, detail="结束时间应晚于开始时间")

    sched.title = req.title
    sched.start_time = req.start_time
    sched.end_time = req.end_time
    sched.completed = req.completed
    sched.category = req.category
    db.commit()
    db.refresh(sched)

    return schedule_to_dict(sched)


@router.delete("/schedules/{sched_id}")
def delete_schedule(
    sched_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    
    sched = get_owned_schedule(db, sched_id, current_user)

    db.delete(sched)
    db.commit()
    return {"message": "删除成功"}


@router.patch("/schedules/{sched_id}/toggle_completed")
def toggle_completed(
    sched_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    
    sched = get_owned_schedule(db, sched_id, current_user)

    sched.completed = not sched.completed  
    db.commit()
    db.refresh(sched)

    return schedule_to_dict(sched)


@router.patch("/schedules/complete_all")
def complete_all_schedules(
    date: str = "",  
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    
    day = parse_day(date)  
    
    stmt = (
        update(models.Schedule)
        .where(
            models.Schedule.user_id == current_user.id,
            models.Schedule.start_time >= day,
            models.Schedule.start_time < day + timedelta(days=1),
        )
        .values(completed=True)
    )
    result = db.execute(stmt)  
    db.commit()

    return {"updated": result.rowcount, "date": date}