
from __future__ import annotations  

from datetime import date, datetime  

from sqlalchemy import (  
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship  

from database import Base, SessionLocal, engine  


class User(Base):
    

    __tablename__ = "users"  
    __table_args__ = {"sqlite_autoincrement": True}  

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)  
    password_hash: Mapped[str] = mapped_column(String, nullable=False)  
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)  

    
    logs: Mapped[list[Log]] = relationship(back_populates="user")  
    schedules: Mapped[list[Schedule]] = relationship(back_populates="user")  
    preferences: Mapped[Preference] = relationship(back_populates="user", uselist=False)  
    recommendations: Mapped[list[Recommendation]] = relationship(back_populates="user")  
    library_items: Mapped[list[UserLibrary]] = relationship(back_populates="user")  


class Log(Base):
    

    __tablename__ = "logs"  

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)  
    date: Mapped[date] = mapped_column(Date, nullable=False)  
    mood_score: Mapped[int] = mapped_column(Integer, nullable=False)  
    content: Mapped[str] = mapped_column(Text, nullable=True)  
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)  

    user: Mapped[User] = relationship(back_populates="logs")  
    tags: Mapped[list[Tag]] = relationship(secondary="log_tags", back_populates="logs")  
    emotion_scores: Mapped[list[EmotionScore]] = relationship(back_populates="log")  


class Tag(Base):
    

    __tablename__ = "tags"  

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)  
    category: Mapped[str] = mapped_column(String, nullable=False, default="event")  

    logs: Mapped[list[Log]] = relationship(secondary="log_tags", back_populates="tags")  


class LogTag(Base):
    

    __tablename__ = "log_tags"  

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  
    log_id: Mapped[int] = mapped_column(ForeignKey("logs.id"), nullable=False)  
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), nullable=False)  

    
    __table_args__ = (UniqueConstraint("log_id", "tag_id", name="uq_log_tag"),)


class EmotionScore(Base):
    

    __tablename__ = "emotion_scores"  

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  
    log_id: Mapped[int] = mapped_column(ForeignKey("logs.id"), nullable=False)  
    emotion_name: Mapped[str] = mapped_column(String, nullable=False)  
    score: Mapped[int] = mapped_column(Integer, nullable=False)  

    log: Mapped[Log] = relationship(back_populates="emotion_scores")  


class Schedule(Base):
    

    __tablename__ = "schedules"  

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)  
    title: Mapped[str] = mapped_column(String, nullable=False)  
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)  
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)  
    completed: Mapped[bool] = mapped_column(Boolean, default=False)  
    category: Mapped[str] = mapped_column(String, nullable=False, default="life")  
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)  

    user: Mapped[User] = relationship(back_populates="schedules")  


class Preference(Base):
    

    __tablename__ = "preferences"  

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)  
    movie_genre: Mapped[str] = mapped_column(String, nullable=True)  
    book_genre: Mapped[str] = mapped_column(String, nullable=True)  
    exercise_type: Mapped[str] = mapped_column(String, nullable=True)  
    free_time_note: Mapped[str] = mapped_column(String, nullable=True)  
    exercise_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=True)  
    reading_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=True)  
    relax_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=True)  

    
    __table_args__ = (UniqueConstraint("user_id", name="uq_preference_user_id"),)

    user: Mapped[User] = relationship(back_populates="preferences")  


class UserLibrary(Base):
    

    __tablename__ = "user_library"
    __table_args__ = (
        UniqueConstraint("user_id", "item_type", "title", name="uq_user_library_item"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)  
    item_type: Mapped[str] = mapped_column(String, nullable=False)  
    title: Mapped[str] = mapped_column(String, nullable=False)  
    status: Mapped[str] = mapped_column(String, nullable=False)  
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)  
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )  

    user: Mapped[User] = relationship(back_populates="library_items")  


class Recommendation(Base):
    

    __tablename__ = "recommendations"  

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)  
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=True)  
    activity_type: Mapped[str] = mapped_column(String, nullable=True)  
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=True)  
    title: Mapped[str | None] = mapped_column(String, nullable=True)  
    item_type: Mapped[str | None] = mapped_column(String, nullable=True)  
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)  

    
    
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  
    scheduled_start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  
    scheduled_end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)  
    feedback_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  

    user: Mapped[User] = relationship(back_populates="recommendations")  




DEFAULT_EMOTION_TAGS = [
    "快乐", "开心", "平静", "喜悦", "愤怒", "焦虑",
    "悲伤", "烦躁", "疲惫", "难过", "紧张", "兴奋",
    "尴尬", "孤独",
]


DEFAULT_EVENT_TAGS = [
    "学习", "工作", "社交", "阅读", "旅行", "饮食",
    "娱乐", "加班", "熬夜", "运动", "睡眠", "购物",
    "家务", "就医", "争吵", "失眠",
]


def init_default_tags() -> None:
    
    db = SessionLocal()
    try:
        
        for category, names in (("emotion", DEFAULT_EMOTION_TAGS), ("event", DEFAULT_EVENT_TAGS)):
            for name in names:
                
                exists = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
                if exists is None:  
                    db.add(Tag(name=name, category=category))
        db.commit()  
    finally:
        db.close()  


def init_db() -> None:
    
    
    db = SessionLocal()
    try:
        existing = db.execute(select(User.id).limit(1)).scalar_one_or_none()
    finally:
        db.close()

    if existing is not None:
        
        return

    
    with engine.connect() as conn:
        
        row = conn.execute(
            text("SELECT name FROM sqlite_sequence WHERE name = 'users'")
        ).first()
        if row is None:
            
            conn.execute(
                text("INSERT INTO sqlite_sequence (name, seq) VALUES ('users', 5310000)")
            )
        else:
            
            conn.execute(
                text("UPDATE sqlite_sequence SET seq = 5310000 WHERE name = 'users'")
            )
        conn.commit()  