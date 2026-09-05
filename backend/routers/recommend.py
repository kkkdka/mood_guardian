
import json
import os
import random
import re
from datetime import date, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

import models
from database import get_db
from routers.auth import get_current_user
from utils import find_free_slots
from recommendation_catalog import BOOKS, EXERCISES, MOVIES, RELAX_ACTIVITIES
from schemas import RecommendRequest, RecommendResponse

router = APIRouter(prefix="/api", tags=["recommend"])

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


def _exercise_leaves(raw: str | None) -> list[str]:
    
    if not raw:
        return []
    try:
        paths = json.loads(raw)
        return [path[-1] for path in paths if isinstance(path, list) and len(path) >= 2]
    except (json.JSONDecodeError, TypeError):
        return [item.strip() for item in raw.replace("、", ",").split(",") if item.strip()]


def _parse_exercise_type(raw: str | None) -> str:
    
    if not raw:
        return "瑜伽"
    leaves = _exercise_leaves(raw)
    return "、".join(leaves) if leaves else raw

COMMON_MOVIES = sum(MOVIES.values(), [])
COMMON_BOOKS = sum(BOOKS.values(), [])

GENERIC_TITLES = {
    "电影推荐",
    "读书推荐",
    "阅读",
    "运动放松",
    "运动",
    "舒缓放松",
    "放松",
    "治愈建议",
}


def _has_specific_title(result: dict, activity_type: str) -> bool:
    title = result.get("title")
    if not isinstance(title, str) or not title.strip():
        return False
    title = title.strip()
    if title in GENERIC_TITLES:
        return False
    if activity_type in {"movie", "book"} and title in {"电影", "书籍"}:
        return False
    return True


def _preference_items(preference: str | None, catalog: dict[str, list[str]], fallback: list[str]) -> list[str]:
    if not preference:
        return fallback
    selected = []
    for genre in preference.split(","):
        selected.extend(catalog.get(genre.strip(), []))
    return list(dict.fromkeys(selected)) or fallback


def _unused_choice(
    items: list[str],
    previous_suggestion: str | None,
    recent_texts: list[str],
    used_titles: set[str] | None = None,
) -> str | None:
    
    previous_suggestion = previous_suggestion or ""
    used = [text for text in recent_texts if text]
    used_titles = used_titles or set()
    candidates = [
        item for item in items
        if item not in previous_suggestion
        and item not in used_titles
        and all(item not in text for text in used)
    ]
    return random.choice(candidates) if candidates else None


def _save_recommendation(db: Session, user_id: int, result: dict) -> int:
    
    db.execute(
        delete(models.Recommendation)
        .where(models.Recommendation.user_id == user_id)
        .where(models.Recommendation.status == "pending")
    )

    rec = models.Recommendation(
        user_id=user_id,
        recommendation_text=result["suggestion"],
        activity_type=result["activity_type"],
        duration_minutes=result["duration_minutes"],
        title=result.get("title"),
        item_type=result.get("item_type"),
    )

    db.add(rec)
    db.flush()  
    rec_id = rec.id
    db.commit()
    return rec_id


def call_deepseek(prompt: str) -> dict | None:
    
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:  
        return None

    try:
        resp = httpx.post(
            DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=10.0,  
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()
        return json.loads(content)
    except Exception:
        
        return None


def _format_date(d: date) -> str:
    
    today = date.today()
    diff = (d - today).days
    if diff == 0:
        return "今天"
    if diff == 1:
        return f"明天（{d.month}月{d.day}日）"
    if diff == 2:
        return f"后天（{d.month}月{d.day}日）"
    return f"{d.month}月{d.day}日"


def format_slot(start_dt: datetime, end_dt: datetime) -> str:
    
    d_start = start_dt.date()
    d_end = end_dt.date()
    if d_start == d_end:
        return f"{_format_date(d_start)} {start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"
    
    return f"{_format_date(d_start)} {start_dt.strftime('%H:%M')}-{_format_date(d_end)} {end_dt.strftime('%H:%M')}"


def _clip_to_waking_hours(
    slots: list[tuple[datetime, datetime]],
    wake_start: int = 7,
    wake_end: int = 23,
) -> list[tuple[datetime, datetime]]:
    
    clipped: list[tuple[datetime, datetime]] = []
    for start, end in slots:
        cursor = start
        while cursor < end:
            
            day_wake_start = cursor.replace(hour=wake_start, minute=0, second=0, microsecond=0)
            day_wake_end = cursor.replace(hour=wake_end, minute=0, second=0, microsecond=0)

            
            if cursor < day_wake_start:
                cursor = day_wake_start

            
            if cursor >= day_wake_end:
                cursor = (cursor + timedelta(days=1)).replace(
                    hour=wake_start, minute=0, second=0, microsecond=0
                )
                continue

            
            slot_end = min(end, day_wake_end)
            if cursor < slot_end:
                clipped.append((cursor, slot_end))
            cursor = slot_end  
    return clipped


def fallback_recommendation(
    free_time_minutes: int,
    slot_text: str = "",
    previous_suggestion: str | None = None,
    movie_genre: str | None = None,
    book_genre: str | None = None,
    exercise_preferences: list[str] | None = None,
    recent_texts: list[str] | None = None,
    used_titles: set[str] | None = None,
    reading_books: list[str] | None = None,
    preferred_type: str | None = None,
    exercise_duration_minutes: int = 30,
    reading_duration_minutes: int = 45,
    relax_duration_minutes: int = 20,
    want_to_watch_movies: list[str] | None = None,
    want_to_read_books: list[str] | None = None,
) -> dict:
    
    prefix = f"观察到您{slot_text}为空闲时段，" if slot_text else ""
    previous_suggestion = previous_suggestion or ""
    recent_texts = recent_texts or []

    if free_time_minutes <= 0:
        return {
            "suggestion": "当前没有合适的清醒空闲时段，建议先完成休息和必要安排。",
            "activity_type": "relax",
            "duration_minutes": 0,
            "title": None,
            "item_type": None,
        }

    movie_pool = want_to_watch_movies or _preference_items(movie_genre, MOVIES, COMMON_MOVIES)
    
    book_pool = want_to_read_books or reading_books or _preference_items(book_genre, BOOKS, COMMON_BOOKS)
    exercise_pool = exercise_preferences or EXERCISES
    options = [(RELAX_ACTIVITIES, "relax", min(relax_duration_minutes, free_time_minutes))]
    if free_time_minutes >= 15:
        options.append((exercise_pool, "exercise", min(exercise_duration_minutes, free_time_minutes)))
    if free_time_minutes >= 30:
        options.append((book_pool, "book", min(reading_duration_minutes, free_time_minutes)))
    if free_time_minutes >= 90:
        options.append((movie_pool, "movie", min(120, free_time_minutes)))

    
    if preferred_type:
        options.sort(key=lambda option: 0 if option[1] == preferred_type else 1)
    else:
        random.shuffle(options)
    for pool, activity_type, duration in options:
        item = _unused_choice(pool, previous_suggestion, recent_texts, used_titles)
        if item is None:
            continue
        if activity_type == "movie":
            text = f"推荐观看电影《{item}》约 {duration} 分钟，让故事帮您转换一下心境。"
        elif activity_type == "book":
            if reading_books and item in reading_books:
                text = f"上次的《{item}》读完了吗？如果没有可以继续阅读哦~ 建议阅读 {duration} 分钟。"
            else:
                text = f"推荐阅读《{item}》约 {duration} 分钟，安静地把注意力放回文字。"
        elif activity_type == "exercise":
            text = f"试试 {duration} 分钟{item}，用适度活动舒展身体、恢复精力。"
        else:
            text = f"用 {duration} 分钟{item}，给紧绷的情绪留一点缓冲。"
        suggestion = f"{prefix}{text}"
        if suggestion != previous_suggestion:
            return {
                "suggestion": suggestion,
                "activity_type": activity_type,
                "duration_minutes": duration,
                "title": item if activity_type in {"movie", "book", "exercise", "relax"} else None,
                "item_type": activity_type if activity_type in {"movie", "book"} else None,
            }

    return {
        "suggestion": f"{prefix}用 5 分钟做腹式深呼吸，让自己暂时慢下来。",
        "activity_type": "relax",
        "duration_minutes": min(5, free_time_minutes),
        "title": "腹式深呼吸",
        "item_type": None,
    }


def _valid_recommendation(
    result: dict | None,
    free_time_minutes: int,
    previous_suggestion: str = "",
    recent_texts: list[str] | None = None,
    used_titles: set[str] | None = None,
    reading_books: list[str] | None = None,
    watched_movies: list[str] | None = None,
    finished_books: list[str] | None = None,
    want_to_watch_movies: list[str] | None = None,
    want_to_read_books: list[str] | None = None,
    exercise_duration_minutes: int = 30,
    reading_duration_minutes: int = 45,
    relax_duration_minutes: int = 20,
) -> bool:
    
    if not isinstance(result, dict):
        return False
    activity_type = result.get("activity_type")
    if activity_type not in {"movie", "book", "exercise", "relax"}:
        return False
    duration = result.get("duration_minutes")
    suggestion = result.get("suggestion")
    if not isinstance(suggestion, str) or not suggestion.strip():
        return False
    if not _has_specific_title(result, activity_type):
        return False
    if suggestion == previous_suggestion or suggestion in (recent_texts or []):
        return False
    if not isinstance(duration, int) or duration <= 0 or duration > free_time_minutes:
        return False
    if activity_type == "movie":
        required_duration = 90 if duration <= 90 else ((duration + 29) // 30) * 30
        if required_duration > free_time_minutes:
            return False
    if activity_type == "exercise":
        if abs(duration - exercise_duration_minutes) > 10:
            return False
    elif activity_type == "book":
        expected_duration = min(reading_duration_minutes, free_time_minutes)
        if duration != expected_duration:
            return False
    elif activity_type == "relax":
        expected_duration = min(relax_duration_minutes, free_time_minutes)
        if duration != expected_duration:
            return False

    if activity_type in {"movie", "book"}:
        title = result.get("title")
        item_type = result.get("item_type")
        if not isinstance(title, str) or not title.strip() or item_type != activity_type:
            return False
        if activity_type == "movie" and title.strip() in (watched_movies or []):
            return False
        if activity_type == "movie" and want_to_watch_movies and title.strip() not in want_to_watch_movies:
            return False
        if activity_type == "book":
            if title.strip() in (finished_books or []):
                return False
            if want_to_read_books and title.strip() not in want_to_read_books:
                return False
            if not want_to_read_books and reading_books and title.strip() not in reading_books:
                return False
    elif result.get("item_type") is not None:
        
        return False
    if free_time_minutes < 20:
        return activity_type == "relax" and duration <= 10
    if free_time_minutes < 45:
        return activity_type != "movie"
    return True


def _preferred_activity_type(free_time_minutes: int, recent_types: list[str]) -> str:
    
    
    available = ["relax"]
    if free_time_minutes >= 15:
        available.append("exercise")
    if free_time_minutes >= 30:
        available.append("book")
    if free_time_minutes >= 90:
        available.append("movie")

    last_type = recent_types[0] if recent_types else None
    if last_type in available:
        next_index = (available.index(last_type) + 1) % len(available)
        return available[next_index]
    return available[0]


def _fit_slot_to_duration(
    slot_start: datetime | None,
    slot_end: datetime | None,
    duration_minutes: int,
) -> tuple[datetime | None, datetime | None]:
    
    if slot_start is None or slot_end is None or duration_minutes <= 0:
        return None, None
    duration = min(
        duration_minutes,
        int((slot_end - slot_start).total_seconds() // 60),
    )
    if duration <= 0:
        return None, None
    return slot_start, slot_start + timedelta(minutes=duration)


def _movie_duration_minutes(movie_minutes: int, free_time_minutes: int) -> int:
    
    if movie_minutes <= 90:
        scheduled = 90
    else:
        scheduled = ((movie_minutes + 29) // 30) * 30
    return min(scheduled, free_time_minutes)


def _scheduled_duration(
    result: dict,
    free_time_minutes: int,
    slot_start: datetime | None,
    slot_end: datetime | None,
) -> int:
    
    activity_type = result.get("activity_type")
    if activity_type == "movie":
        duration = _movie_duration_minutes(
            int(result.get("duration_minutes", 0) or 0),
            free_time_minutes,
        )
    else:
        duration = min(int(result.get("duration_minutes", 0) or 0), free_time_minutes)
    if slot_start is not None and slot_end is not None:
        duration = min(duration, int((slot_end - slot_start).total_seconds() // 60))
    return max(duration, 0)


def _slot_text_for_duration(
    slot_start: datetime | None,
    slot_end: datetime | None,
    duration_minutes: int,
) -> str:
    fitted_start, fitted_end = _fit_slot_to_duration(slot_start, slot_end, duration_minutes)
    if fitted_start is None or fitted_end is None:
        return "暂无空闲时段"
    return format_slot(fitted_start, fitted_end)


def _replace_slot_text(suggestion: str, slot_text: str) -> str:
    
    return re.sub(
        r"^观察到您.*?为空闲时段，",
        f"观察到您{slot_text}为空闲时段，",
        suggestion,
        count=1,
    )


def _suggested_times(slot_start: datetime | None, duration_minutes: int) -> tuple[str | None, str | None]:
    
    if slot_start is None or duration_minutes <= 0:
        return None, None
    end = slot_start + timedelta(minutes=duration_minutes)
    return slot_start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")


@router.post("/recommend", response_model=RecommendResponse)
def recommend(
    req: RecommendRequest | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    now = datetime.now()

    
    scores = db.execute(
        select(models.Log.mood_score)
        .where(models.Log.user_id == current_user.id)
        .where(models.Log.date >= date.today() - timedelta(days=2))
    ).scalars().all()
    avg_mood = round(sum(scores) / len(scores), 2) if scores else None

    
    end_48h = now + timedelta(hours=48)
    schedules = db.execute(
        select(models.Schedule)
        .where(models.Schedule.user_id == current_user.id)
        .where(models.Schedule.end_time >= now)        
        .where(models.Schedule.start_time <= end_48h)  
    ).scalars().all()
    schedule_list = [{"start": s.start_time, "end": s.end_time} for s in schedules]
    free_slots = find_free_slots(schedule_list, now, end_48h)

    
    free_slots = _clip_to_waking_hours(free_slots)

    
    total_free_minutes = int(sum((e - s).total_seconds() for s, e in free_slots) // 60)
    
    earliest_start_hour = free_slots[0][0].hour if free_slots else 24

    if free_slots:
        slot_start, slot_end = free_slots[0]  
        free_time_minutes = int((slot_end - slot_start).total_seconds() // 60)
        free_slot_text = format_slot(slot_start, slot_end)  
    else:
        slot_start = None  
        slot_end = None
        free_time_minutes = 0
        free_slot_text = "暂无空闲时段"

    
    pref = db.execute(
        select(models.Preference).where(models.Preference.user_id == current_user.id)
    ).scalar_one_or_none()
    movie_genre = pref.movie_genre if (pref and pref.movie_genre) else None
    book_genre = pref.book_genre if (pref and pref.book_genre) else None
    exercise_raw = pref.exercise_type if (pref and pref.exercise_type) else None
    exercise_preferences = _exercise_leaves(exercise_raw)
    exercise_type = _parse_exercise_type(exercise_raw)
    exercise_duration_minutes = (pref.exercise_duration_minutes if pref and pref.exercise_duration_minutes else 30)
    reading_duration_minutes = (pref.reading_duration_minutes if pref and pref.reading_duration_minutes else 45)
    relax_duration_minutes = (pref.relax_duration_minutes if pref and pref.relax_duration_minutes else 20)
    recent_texts = db.execute(
        select(models.Recommendation.recommendation_text)
        .where(models.Recommendation.user_id == current_user.id)
        .order_by(desc(models.Recommendation.created_at), desc(models.Recommendation.id))
        .limit(20)
    ).scalars().all()
    
    
    
    recent_activity_types = db.execute(
        select(models.Recommendation.activity_type)
        .where(models.Recommendation.user_id == current_user.id)
        .order_by(desc(models.Recommendation.created_at), desc(models.Recommendation.id))
        .limit(6)
    ).scalars().all()
    recent_activity_text = "、".join(t for t in recent_activity_types if t) or "暂无"
    
    preferred_type = _preferred_activity_type(total_free_minutes, recent_activity_types)
    
    library_items = db.execute(
        select(models.UserLibrary)
        .where(models.UserLibrary.user_id == current_user.id)
    ).scalars().all()
    accepted_media = db.execute(
        select(models.Recommendation)
        .where(models.Recommendation.user_id == current_user.id)
        .where(models.Recommendation.item_type.in_({"movie", "book"}))
        .where(models.Recommendation.status.in_({"accepted", "completed", "feedback_given"}))
        .where(models.Recommendation.title.is_not(None))
    ).scalars().all()

    want_to_watch_movies = list(dict.fromkeys(
        item.title for item in library_items
        if item.item_type == "movie" and item.status == "want_to_watch"
    ))
    watched_movies = list(dict.fromkeys(
        [item.title for item in library_items if item.item_type == "movie" and item.status == "watched"]
        + [item.title for item in accepted_media if item.item_type == "movie"]
    ))
    want_to_read_books = list(dict.fromkeys(
        item.title for item in library_items
        if item.item_type == "book" and item.status == "want_to_read"
    ))
    reading_books = list(dict.fromkeys(
        [item.title for item in library_items if item.item_type == "book" and item.status == "reading"]
        + [item.title for item in accepted_media if item.item_type == "book"]
    ))
    finished_books = list(dict.fromkeys(
        [item.title for item in library_items if item.item_type == "book" and item.status == "finished"]
    ))
    watched_title_set = set(watched_movies)
    finished_title_set = set(finished_books)
    
    want_to_watch_movies = [title for title in want_to_watch_movies if title not in watched_title_set]
    want_to_read_books = [title for title in want_to_read_books if title not in finished_title_set]
    reading_books = [title for title in reading_books if title not in finished_title_set]
    
    used_titles = set(watched_movies + finished_books)

    
    busy = total_free_minutes < 60
    late_and_busy = earliest_start_hour >= 21 and total_free_minutes < 120
    too_late = now.hour >= 22
    no_free = len(free_slots) == 0
    if busy or late_and_busy or too_late or no_free:
        result = fallback_recommendation(
            free_time_minutes,
            free_slot_text,
            req.previous_suggestion if req else "",
            movie_genre,
            book_genre,
            exercise_preferences,
            recent_texts,
            used_titles,
            reading_books,
            preferred_type,
            exercise_duration_minutes,
            reading_duration_minutes,
            relax_duration_minutes,
            want_to_watch_movies,
            want_to_read_books,
        )
        scheduled_duration = _scheduled_duration(
            result,
            free_time_minutes,
            slot_start,
            slot_end,
        )
        result["duration_minutes"] = scheduled_duration
        result["suggestion"] = _replace_slot_text(
            result["suggestion"],
            _slot_text_for_duration(slot_start, slot_end, scheduled_duration),
        )
        rec_id = _save_recommendation(db, current_user.id, result)
        suggested_start, suggested_end = _suggested_times(slot_start, scheduled_duration)
        return {
            **result,
            "id": rec_id,
            "suggested_start_time": suggested_start,
            "suggested_end_time": suggested_end,
            "avg_mood": avg_mood,
            "free_time_minutes": total_free_minutes,
        }

    
    example_movie = random.choice(COMMON_MOVIES)
    example_book = random.choice(COMMON_BOOKS)

    
    if free_time_minutes < 20:
        time_rule = (
            f"8. 空闲时长仅 {free_time_minutes} 分钟，只能推荐「深呼吸、短暂冥想、听一首歌」等 5-10 分钟内的微型活动，"
            "不推荐任何电影或书籍；"
        )
    elif free_time_minutes < 45:
        time_rule = (
            f"8. 空闲时长 {free_time_minutes} 分钟，可以推荐「看一集 20 分钟短剧、阅读 10 页小说、"
            "快走 15 分钟、冥想 10 分钟」等，不推荐完整电影；"
        )
    elif free_time_minutes < 90:
        time_rule = (
            f"8. 空闲时长 {free_time_minutes} 分钟，可以推荐「90 分钟以内的电影、阅读 30 分钟、"
            "瑜伽 30 分钟」等；若推荐电影，必须确保片长严格不超过空闲时间；"
        )
    else:
        time_rule = (
            f"8. 空闲时长 {free_time_minutes} 分钟，可以推荐「完整电影、较长运动、深度阅读」等，"
            "但电影时长不能超过空闲时间（若略超，建议分段观看）；"
        )

    
    example_title = {
        "movie": "流浪地球2",
        "book": "被讨厌的勇气",
        "exercise": "羽毛球",
        "relax": "腹式深呼吸",
    }.get(preferred_type, "腹式深呼吸")
    example_item_type = (
        preferred_type
        if preferred_type in {"movie", "book"}
        else "null"
    )
    prompt = (
        "你是一位温暖的心理治愈助手。请根据以下信息，给用户提供一条情绪调节建议：\n"
        f"- 最近3天平均心情评分：{avg_mood if avg_mood is not None else '暂无数据'}（满分10分，仅供你判断情绪程度，不要写进文案）\n"
        f"- 未来48小时内的空闲时段：{free_slot_text}（约 {free_time_minutes} 分钟）\n"
        f"- 偏好：电影类型「{movie_genre or '无'}」，书籍类型「{book_genre or '无'}」，运动类型「{exercise_type}」\n"
        f"- 用户时长偏好：运动 {exercise_duration_minutes} 分钟，阅读 {reading_duration_minutes} 分钟，放松 {relax_duration_minutes} 分钟\n"
        f"- 最近已推荐内容（不要重复）：{recent_texts or '暂无'}\n"
        f"- 想看电影（电影推荐优先从中选择）：{want_to_watch_movies or '暂无'}\n"
        f"- 已看电影（电影推荐必须排除）：{watched_movies or '暂无'}\n"
        f"- 想读书籍（书籍推荐优先从中选择）：{want_to_read_books or '暂无'}\n"
        f"- 在读书籍（没有想读书籍时优先继续阅读）：{reading_books or '暂无'}\n"
        f"- 已读书籍（推荐新书时必须排除）：{finished_books or '暂无'}\n\n"
        "请严格遵守以下要求：\n"
        f"0. 本次活动类型务必推荐「{preferred_type}」，不要推荐其他类型；"
        f"最近已推荐过的活动类型依次为「{recent_activity_text}」，请保持电影、读书、运动、放松之间的交替，避免单一类型连续出现；\n"
        f"1. 建议必须以「观察到您{free_slot_text}为空闲时段，……」开头，明确点出这个具体时间段；\n"
        "2. 如果推荐电影，优先从用户想看电影列表中选择；如果列表为空，才从用户未看过的其他电影中选择。必须排除已看电影，并在 title 中填写具体电影名；"
        "如果没有合适的电影，可以改推荐其他活动类型；\n"
        "3. 如果推荐书籍，优先从用户想读书籍列表中选择；如果列表为空且存在在读书籍，必须推荐其中一本继续阅读；"
        "继续阅读时文案必须询问‘上次的《XXX》读完了吗？如果没有可以继续阅读哦~’，并将 XXX 替换为实际书名；"
        "只有没有想读和在读书籍时，才可从未读过的新书中选择，并排除已读书籍；"
        "如果过滤后没有合适书籍，可以改推荐其他活动类型；\n"
        "4. 若推荐电影或书籍，必须给出具体名称（1 部或 1 本），且该作品的真实完整时长绝对不能超过空闲时段；"
        "空闲不足以完整看完时，应改为推荐短时活动（如冥想、散步、听歌、看短视频）或明确说明可分段观看，"
        "绝不能推荐时长远超空闲的作品（例如空闲仅60分钟却推荐近3小时的《星际穿越》）；\n"
        "3. duration_minutes 必须是真实可行的时长：电影按真实片长填写（一般 90-150 分钟），"
        "书籍/运动/放松按实际所需时间填写，不得为了不超过空闲时段而虚构或缩短作品的真实时长；\n"
        "4. 用一句话简短说明选择理由（为什么适合现在的用户）；\n"
        f"5. 若用户没有电影/书籍偏好，请从常见高分作品中自行选择，例如电影《{example_movie}》或书籍《{example_book}》。\n"
        "6. 如果用户空闲时间很零碎或整体较少，请建议一些轻松恢复精力的小活动（如5分钟冥想），并提醒不要熬夜；\n"
        "7. 建议文案中严禁出现用户的情绪评分数字（如6.25分），也不要写「适合您目前多少分的情绪状态」这类话，"
        "可用「情绪状态」等模糊说法表达关怀。\n"
        f"{time_rule}\n"
        f"运动推荐时长应接近用户偏好的 {exercise_duration_minutes} 分钟（允许上下浮动10分钟）；"
        f"阅读推荐时长固定为 {reading_duration_minutes} 分钟；放松推荐时长使用 {relax_duration_minutes} 分钟；"
        "电影时长按电影真实片长安排，不受上述偏好限制。\n"  
        "请只返回一个 JSON 对象（不要包含任何其他文字或代码块标记），包含以下五个字段：\n"
        '1. "suggestion"：一段治愈建议（以具体时间段开头，含具体电影名/书名和简短理由）；\n'
        '2. "activity_type"：建议的活动类型，只能取 movie / book / exercise / relax 之一；\n'
        '3. "duration_minutes"：建议时长（整数，单位分钟）；\n'
        '4. "title"：一个简短且具体的活动名称。电影必须填真实电影名，书籍必须填真实书名，'
        '运动必须填具体运动名（如「羽毛球」「骑行」），放松必须填具体内容（如「腹式深呼吸」「听白噪音」「身体扫描」），'
        '禁止填写「电影推荐」「读书推荐」「运动放松」「舒缓放松」「放松」等笼统分类名称；\n'
        '5. "item_type"：若推荐电影填写 movie，若推荐书籍填写 book，其他活动必须为 null。\n'
        "电影不得使用“已看电影”列表中的标题；电影有想看项时必须从“想看电影”列表中选择；"
        "书籍有想读项时必须从“想读书籍”列表中选择；没有想读项但有在读项时必须从在读书籍中选择；"
        "只有没有想读和在读项时，才可推荐新书，且不得使用“已读书籍”列表中的标题。\n"
        f'输出示例（activity_type 必须为 {preferred_type}）：{{"suggestion": "观察到您今天 19:00-21:00 为空闲时段，推荐……", "activity_type": "{preferred_type}", "duration_minutes": 30, "title": "{example_title}", "item_type": {example_item_type}}}'
    )

    
    result = call_deepseek(prompt)
    ai_type_ok = isinstance(result, dict) and result.get("activity_type") == preferred_type
    if not _valid_recommendation(
        result,
        free_time_minutes,
        req.previous_suggestion if req else "",
        recent_texts,
        used_titles,
        reading_books,
        watched_movies,
        finished_books,
        want_to_watch_movies,
        want_to_read_books,
        exercise_duration_minutes,
        reading_duration_minutes,
        relax_duration_minutes,
    ) or not ai_type_ok:
        result = fallback_recommendation(
            free_time_minutes,
            free_slot_text,
            req.previous_suggestion if req else "",
            movie_genre,
            book_genre,
            exercise_preferences,
            recent_texts,
            used_titles,
            reading_books,
            preferred_type,
            exercise_duration_minutes,
            reading_duration_minutes,
            relax_duration_minutes,
            want_to_watch_movies,
            want_to_read_books,
        )

    suggestion = result.get("suggestion", "")
    activity_type = result.get("activity_type", "relax")
    duration_minutes = result.get("duration_minutes", 0)

    scheduled_duration = _scheduled_duration(
        result,
        free_time_minutes,
        slot_start,
        slot_end,
    )
    result["duration_minutes"] = scheduled_duration
    result["suggestion"] = _replace_slot_text(
        suggestion,
        _slot_text_for_duration(slot_start, slot_end, scheduled_duration),
    )
    suggestion = result["suggestion"]
    duration_minutes = scheduled_duration

    
    if avg_mood is not None and avg_mood < 3:
        suggestion += " 如果持续情绪低落，建议和信任的人聊聊或寻求专业帮助。"

    saved_result = {
        "suggestion": suggestion,
        "activity_type": activity_type,
        "duration_minutes": duration_minutes,
        "title": result.get("title") if activity_type in {"movie", "book", "exercise", "relax"} else None,
        "item_type": result.get("item_type") if activity_type in {"movie", "book"} else None,
    }
    rec_id = _save_recommendation(db, current_user.id, saved_result)
    suggested_start, suggested_end = _suggested_times(slot_start, saved_result.get("duration_minutes", 0))
    return {
        **saved_result,
        "id": rec_id,
        "suggested_start_time": suggested_start,
        "suggested_end_time": suggested_end,
        "avg_mood": avg_mood,
        "free_time_minutes": free_time_minutes,
    }