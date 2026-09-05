
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

import models
from database import get_db
from routers.auth import get_current_user
from schemas import LibraryReviewRequest, ManualLibraryAddRequest

router = APIRouter(prefix="/api/library", tags=["library"])


def _iso(value: datetime) -> str:
    
    return value.isoformat(timespec="seconds")


@router.post("/manual_add")
def manual_add_library_item(
    payload: ManualLibraryAddRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    if payload.item_type not in {"movie", "book"}:
        raise HTTPException(status_code=400, detail="item_type 必须是 movie 或 book")
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="title 不能为空")

    
    if payload.item_type == "movie":
        status = payload.status or "want_to_watch"
        if status not in {"want_to_watch", "watched"}:
            raise HTTPException(
                status_code=400,
                detail="电影 status 必须是 want_to_watch 或 watched",
            )
    else:
        status = payload.status or "want_to_read"
        if status not in {"want_to_read", "reading", "finished"}:
            raise HTTPException(
                status_code=400,
                detail="书籍 status 必须是 want_to_read、reading 或 finished",
            )

    title = payload.title.strip()
    item = db.execute(
        select(models.UserLibrary)
        .where(models.UserLibrary.user_id == current_user.id)
        .where(models.UserLibrary.item_type == payload.item_type)
        .where(models.UserLibrary.title == title)
    ).scalar_one_or_none()
    existed = item is not None
    if item is None:
        item = models.UserLibrary(
            user_id=current_user.id,
            item_type=payload.item_type,
            title=payload.title.strip(),
            status=status,
            created_at=datetime.now(),
        )
        db.add(item)
        db.commit()
        db.refresh(item)

    result = {
        "id": item.id,
        "title": item.title,
        "item_type": item.item_type,
        "status": item.status,
        "created_at": _iso(item.created_at),
    }
    if existed:
        result["message"] = "已存在"
    return result


@router.post("/{item_type}/{title:path}/reviews")
def add_library_review(
    item_type: str,
    title: str,
    payload: LibraryReviewRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    if item_type not in {"movie", "book"}:
        raise HTTPException(status_code=400, detail="item_type 必须是 movie 或 book")

    title = title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="标题不能为空")

    library_item = db.execute(
        select(models.UserLibrary)
        .where(models.UserLibrary.user_id == current_user.id)
        .where(models.UserLibrary.item_type == item_type)
        .where(models.UserLibrary.title == title)
    ).scalar_one_or_none()
    if library_item is None:
        raise HTTPException(status_code=404, detail="该项目不在你的片单或书单中")

    recommendation = models.Recommendation(
        user_id=current_user.id,
        recommendation_text=f"用户手动评价：{title}",
        activity_type=item_type,
        title=title,
        item_type=item_type,
        status="feedback_given",
        rating=payload.rating,
        feedback_text=payload.feedback_text.strip() if payload.feedback_text else None,
        feedback_at=datetime.now(),
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)

    return {
        "message": "评价已保存",
        "review": {
            "id": recommendation.id,
            "rating": recommendation.rating,
            "feedback_text": recommendation.feedback_text,
            "feedback_at": _iso(recommendation.feedback_at),
            "created_at": _iso(recommendation.created_at),
        },
    }


@router.post("/finish_book/{library_id}")
def finish_book(
    library_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    library_item = db.get(models.UserLibrary, library_id)
    if library_item is None or library_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="媒体库记录不存在")
    if library_item.item_type != "book":
        raise HTTPException(status_code=400, detail="该记录不是书籍")
    if library_item.status != "reading":
        raise HTTPException(status_code=400, detail="只有在读书籍可以标记为已读")

    library_item.status = "finished"
    library_item.updated_at = datetime.now()  
    db.commit()
    db.refresh(library_item)

    return {
        "message": "已标记为读完",
        "book": {
            "id": library_item.id,
            "title": library_item.title,
            "status": library_item.status,
            "created_at": _iso(library_item.created_at),
            "updated_at": _iso(library_item.updated_at),
        },
    }


@router.delete("/{library_id}")
def delete_library_item(
    library_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    library_item = db.get(models.UserLibrary, library_id)
    if library_item is None or library_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="媒体库记录不存在")

    db.delete(library_item)
    db.commit()
    return {"message": "已删除"}


@router.get("/movies")
def list_movies(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    movies = db.execute(
        select(models.UserLibrary)
        .where(models.UserLibrary.user_id == current_user.id)
        .where(models.UserLibrary.item_type == "movie")
        .order_by(desc(models.UserLibrary.created_at), desc(models.UserLibrary.id))
    ).scalars().all()

    return [
        {
            "id": movie.id,
            "title": movie.title,
            "status": movie.status,
            "created_at": _iso(movie.created_at),
            "updated_at": _iso(movie.updated_at),
        }
        for movie in movies
    ]


@router.get("/movies/{title:path}/reviews")
def list_movie_reviews(
    title: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    recommendations = db.execute(
        select(models.Recommendation)
        .where(models.Recommendation.user_id == current_user.id)
        .where(models.Recommendation.item_type == "movie")
        .where(models.Recommendation.title == title)
        .where(models.Recommendation.rating.is_not(None))
        .order_by(
            desc(models.Recommendation.feedback_at),
            desc(models.Recommendation.created_at),
            desc(models.Recommendation.id),
        )
    ).scalars().all()

    ratings = [recommendation.rating for recommendation in recommendations]
    average_rating = round(sum(ratings) / len(ratings), 1) if ratings else None

    return {
        "title": title,
        "average_rating": average_rating,
        "review_count": len(recommendations),
        "reviews": [
            {
                "id": recommendation.id,
                "rating": recommendation.rating,
                "feedback_text": recommendation.feedback_text,
                "feedback_at": (
                    _iso(recommendation.feedback_at)
                    if recommendation.feedback_at
                    else None
                ),
                "created_at": _iso(recommendation.created_at),
            }
            for recommendation in recommendations
        ],
    }


@router.get("/books/{title:path}/reviews")
def list_book_reviews(
    title: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    recommendations = db.execute(
        select(models.Recommendation)
        .where(models.Recommendation.user_id == current_user.id)
        .where(models.Recommendation.item_type == "book")
        .where(models.Recommendation.title == title)
        .where(models.Recommendation.rating.is_not(None))
        .order_by(
            desc(models.Recommendation.feedback_at),
            desc(models.Recommendation.created_at),
            desc(models.Recommendation.id),
        )
    ).scalars().all()

    ratings = [recommendation.rating for recommendation in recommendations]
    average_rating = round(sum(ratings) / len(ratings), 1) if ratings else None

    return {
        "title": title,
        "average_rating": average_rating,
        "review_count": len(recommendations),
        "reviews": [
            {
                "id": recommendation.id,
                "rating": recommendation.rating,
                "feedback_text": recommendation.feedback_text,
                "feedback_at": (
                    _iso(recommendation.feedback_at)
                    if recommendation.feedback_at
                    else None
                ),
                "created_at": _iso(recommendation.created_at),
            }
            for recommendation in recommendations
        ],
    }


@router.get("/books")
def list_books(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    books = db.execute(
        select(models.UserLibrary)
        .where(models.UserLibrary.user_id == current_user.id)
        .where(models.UserLibrary.item_type == "book")
        .order_by(desc(models.UserLibrary.created_at), desc(models.UserLibrary.id))
    ).scalars().all()

    return [
        {
            "id": book.id,
            "title": book.title,
            "status": book.status,
            "created_at": _iso(book.created_at),
            "updated_at": _iso(book.updated_at),
        }
        for book in books
    ]
