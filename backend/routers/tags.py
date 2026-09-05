
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
from database import get_db

router = APIRouter(prefix="/api", tags=["tags"])


@router.get("/tags")
def list_tags(db: Session = Depends(get_db)):
    
    tags = db.execute(select(models.Tag)).scalars().all()

    emotion_tags = []
    event_tags = []
    for tag in tags:
        if tag.category == "emotion":
            emotion_tags.append(tag.name)
        else:
            event_tags.append(tag.name)

    return {
        "emotion": emotion_tags,
        "event": event_tags,
    }