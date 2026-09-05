
import re
from datetime import datetime

from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    

    username: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        
        if len(v) < 8 or not re.search(r"[a-zA-Z]", v) or not re.search(r"\d", v):
            raise ValueError("密码需至少8位且包含数字和字母")
        return v


class LoginRequest(BaseModel):
    

    username: str
    password: str


class AnalyzeEmotionRequest(BaseModel):
    

    content: str  


class LogRequest(BaseModel):
    

    date: str             
    mood_score: int       
    content: str          
    tags: list[str] = []  


class EmotionScoreItem(BaseModel):
    

    emotion_name: str  
    score: int         


class LogUpdateRequest(BaseModel):
    

    content: str | None = None                                 
    mood_score: int | None = None                              
    tags: list[str] | None = None                              
    emotion_scores: list[EmotionScoreItem] | None = None       


class PreferencesRequest(BaseModel):
    

    movie_genre: str | None = None    
    book_genre: str | None = None     
    exercise_type: str | None = None  


class RecommendRequest(BaseModel):
    

    previous_suggestion: str | None = None


class ManualLibraryAddRequest(BaseModel):
    

    item_type: str  
    title: str  
    status: str  


class LibraryReviewRequest(BaseModel):
    

    rating: int  
    feedback_text: str | None = None  

    @field_validator("rating")
    @classmethod
    def check_rating(cls, v: int) -> int:
        
        if not 1 <= v <= 10:
            raise ValueError("评分需在 1-10 之间")
        return v


class ScheduleRequest(BaseModel):
    

    title: str             
    start_time: datetime   
    end_time: datetime     
    completed: bool = False  
    category: str = "life"   


class RecommendResponse(BaseModel):
    

    id: int                             
    suggestion: str                     
    activity_type: str                  
    duration_minutes: int               
    title: str | None = None            
    item_type: str | None = None        
    suggested_start_time: str | None = None  
    suggested_end_time: str | None = None    
    avg_mood: float | None = None       
    free_time_minutes: int              


class AcceptRequest(BaseModel):
    

    scheduled_start_time: str | None = None  
    scheduled_end_time: str | None = None    


class FeedbackRequest(BaseModel):
    

    rating: int                       
    feedback_text: str | None = None  

    @field_validator("rating")
    @classmethod
    def check_rating(cls, v: int) -> int:
        
        if not 1 <= v <= 10:
            raise ValueError("评分需在 1-10 之间")
        return v