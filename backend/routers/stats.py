
from datetime import date, datetime
from statistics import mean, stdev

from fastapi import APIRouter, Depends, HTTPException
from scipy import stats as scipy_stats
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import models
from database import get_db
from routers import auth

router = APIRouter(prefix="/api", tags=["stats"])


def parse_date(s: str | None) -> date | None:
    
    if s is None:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")


@router.get("/stats/daily_avg")
def daily_avg(
    start_date: str | None = None,  
    end_date: str | None = None,    
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    start = parse_date(start_date)
    end = parse_date(end_date)

    
    stmt = (
        select(models.Log.date, func.avg(models.Log.mood_score))
        .where(models.Log.user_id == current_user.id)
        .group_by(models.Log.date)
        .order_by(models.Log.date.asc())  
    )
    
    if start is not None:
        stmt = stmt.where(models.Log.date >= start)
    if end is not None:
        stmt = stmt.where(models.Log.date <= end)

    rows = db.execute(stmt).all()  

    dates = []
    avg_scores = []
    for d, avg in rows:
        dates.append(d.strftime("%Y-%m-%d"))      
        avg_scores.append(round(float(avg), 1))   

    
    return {"dates": dates, "avg_scores": avg_scores}


@router.get("/stats/{tag_name}")
def tag_stats(
    tag_name: str,
    start_date: str | None = None,  
    end_date: str | None = None,    
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    start = parse_date(start_date)
    end = parse_date(end_date)

    
    tag = db.execute(select(models.Tag).where(models.Tag.name == tag_name)).scalar_one_or_none()
    if tag is None:
        raise HTTPException(status_code=404, detail="标签不存在")

    
    tagged_ids = select(models.LogTag.log_id).where(models.LogTag.tag_id == tag.id)

    
    stmt_a = (
        select(models.Log.mood_score)
        .where(models.Log.user_id == current_user.id)
        .where(models.Log.id.in_(tagged_ids))
    )
    
    stmt_b = (
        select(models.Log.mood_score)
        .where(models.Log.user_id == current_user.id)
        .where(models.Log.id.not_in(tagged_ids))
    )

    
    if start is not None:
        stmt_a = stmt_a.where(models.Log.date >= start)
        stmt_b = stmt_b.where(models.Log.date >= start)
    if end is not None:
        stmt_a = stmt_a.where(models.Log.date <= end)
        stmt_b = stmt_b.where(models.Log.date <= end)

    scores_a = list(db.execute(stmt_a).scalars().all())
    scores_b = list(db.execute(stmt_b).scalars().all())

    n1 = len(scores_a)
    n2 = len(scores_b)

    
    if n1 < 3 or n2 < 3:
        raise HTTPException(status_code=400, detail="数据不足，无法进行统计")

    mean_a = mean(scores_a)
    mean_b = mean(scores_b)
    std_a = stdev(scores_a)
    std_b = stdev(scores_b)

    
    if n1 >= 10 and n2 >= 10:
        _, p_value = scipy_stats.ttest_ind(scores_a, scores_b)
        test_used = "ttest_ind"
        message = "数据充足，结果可信"
    else:
        _, p_value = scipy_stats.mannwhitneyu(scores_a, scores_b)
        test_used = "mannwhitneyu"
        message = "数据较少，结果仅供参考"

    
    pooled_std = (((n1 - 1) * std_a ** 2 + (n2 - 1) * std_b ** 2) / (n1 + n2 - 2)) ** 0.5
    effect_size = (mean_a - mean_b) / pooled_std if pooled_std else 0.0

    return {
        "tag": tag_name,
        "category": tag.category,
        "group": {"count": n1, "mean": round(mean_a, 2), "std": round(std_a, 2)},
        "control": {"count": n2, "mean": round(mean_b, 2), "std": round(std_b, 2)},
        "p_value": round(float(p_value), 4),
        "effect_size": round(effect_size, 2),
        "test_used": test_used,
        "message": message,
    }