
from calendar import monthrange
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

import models
from database import get_db
from routers import auth

router = APIRouter(prefix="/api/reports", tags=["reports"])


def parse_report_date(value: str | None) -> date:
    
    if not value:
        return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")


def get_period_range(period: str, target: date) -> tuple[date, date]:
    
    if period == "week":
        start = target - timedelta(days=target.weekday())
        return start, start + timedelta(days=6)
    if period == "month":
        start = target.replace(day=1)
        return start, target.replace(day=monthrange(target.year, target.month)[1])
    raise HTTPException(status_code=400, detail="period 只能是 week 或 month")


def iso_date(value: date) -> str:
    return value.isoformat()


@router.get("/summary")
def report_summary(
    period: str = Query("week", pattern="^(week|month)$"),
    target_date: str | None = Query(
        None,
        alias="date",
        description="定位日期，格式 YYYY-MM-DD",
    ),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    
    target = parse_report_date(target_date)
    start_date, end_date = get_period_range(period, target)

    logs = db.execute(
        select(models.Log)
        .where(models.Log.user_id == current_user.id)
        .where(models.Log.date >= start_date)
        .where(models.Log.date <= end_date)
        .order_by(desc(models.Log.date), desc(models.Log.created_at), desc(models.Log.id))
    ).scalars().all()

    scores = [log.mood_score for log in logs if log.mood_score is not None]
    avg_mood = round(sum(scores) / len(scores), 1) if scores else None

    
    daily_scores: dict[date, list[int]] = {}
    for log in logs:
        if log.mood_score is not None:
            daily_scores.setdefault(log.date, []).append(log.mood_score)
    daily_averages = {
        day: round(sum(day_scores) / len(day_scores), 1)
        for day, day_scores in daily_scores.items()
    }
    highest_day = None
    lowest_day = None
    if daily_averages:
        highest = max(daily_averages.items(), key=lambda item: (item[1], item[0]))
        lowest = min(daily_averages.items(), key=lambda item: (item[1], item[0]))
        highest_day = {"date": iso_date(highest[0]), "avg_score": highest[1]}
        lowest_day = {"date": iso_date(lowest[0]), "avg_score": lowest[1]}

    
    tag_rows = db.execute(
        select(
            models.Tag.name,
            models.Tag.category,
            func.count(models.LogTag.id).label("count"),
        )
        .join(models.LogTag, models.LogTag.tag_id == models.Tag.id)
        .join(models.Log, models.Log.id == models.LogTag.log_id)
        .where(models.Log.user_id == current_user.id)
        .where(models.Log.date >= start_date)
        .where(models.Log.date <= end_date)
        .group_by(models.Tag.id, models.Tag.name, models.Tag.category)
        .order_by(desc("count"), models.Tag.name.asc())
        .limit(5)
    ).all()
    top_tags = [
        {"name": name, "category": category, "count": count}
        for name, category, count in tag_rows
    ]

    
    period_start = datetime.combine(start_date, datetime.min.time())
    period_end = datetime.combine(end_date, datetime.max.time())
    schedules = db.execute(
        select(models.Schedule)
        .where(models.Schedule.user_id == current_user.id)
        .where(models.Schedule.start_time <= period_end)
        .where(models.Schedule.end_time >= period_start)
    ).scalars().all()
    total_count = len(schedules)
    completed_count = sum(1 for schedule in schedules if schedule.completed)
    completion_rate = (
        round(completed_count / total_count * 100, 1)
        if total_count
        else None
    )

    return {
        "period": period,
        "start_date": iso_date(start_date),
        "end_date": iso_date(end_date),
        "avg_mood": avg_mood,
        "highest_day": highest_day,
        "lowest_day": lowest_day,
        "log_count": len(logs),
        "top_tags": top_tags,
        "schedule": {
            "completed_count": completed_count,
            "total_count": total_count,
            "completion_rate": completion_rate,
        },
    }
