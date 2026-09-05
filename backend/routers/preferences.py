
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
from database import get_db
from routers import auth
from schemas import PreferencesRequest

router = APIRouter(prefix="/api", tags=["preferences"])


@router.post("/preferences")
def save_preferences(
    req: PreferencesRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    
    
    pref = db.execute(
        select(models.Preference).where(models.Preference.user_id == current_user.id)
    ).scalar_one_or_none()

    if pref is None:
        
        pref = models.Preference(
            user_id=current_user.id,
            movie_genre=req.movie_genre,
            book_genre=req.book_genre,
            exercise_type=req.exercise_type,
        )
        db.add(pref)
    else:
        
        pref.movie_genre = req.movie_genre
        pref.book_genre = req.book_genre
        pref.exercise_type = req.exercise_type

    db.commit()
    db.refresh(pref)  

    return {
        "user_id": pref.user_id,
        "movie_genre": pref.movie_genre,
        "book_genre": pref.book_genre,
        "exercise_type": pref.exercise_type,
    }


@router.get("/preferences")
def get_preferences(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    
    pref = db.execute(
        select(models.Preference).where(models.Preference.user_id == current_user.id)
    ).scalar_one_or_none()

    if pref is None:
        return {
            "user_id": current_user.id,
            "movie_genre": "",
            "book_genre": "",
            "exercise_type": "",
        }

    
    return {
        "user_id": pref.user_id,
        "movie_genre": pref.movie_genre or "",
        "book_genre": pref.book_genre or "",
        "exercise_type": pref.exercise_type or "",
    }