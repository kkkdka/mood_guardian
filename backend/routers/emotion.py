
import json
import os

import httpx
from fastapi import APIRouter

from schemas import AnalyzeEmotionRequest

router = APIRouter(prefix="/api", tags=["emotion"])


DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


def call_deepseek_emotions(content: str) -> list[str] | None:
    
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:  
        return None

    prompt = (
        "请分析下面这段日记文本中蕴含的情绪，并提取情绪关键词。\n"
        "只返回一个 JSON 字符串数组，例如 [\"焦虑\", \"疲惫\"]。\n"
        "不要输出任何多余的文字、解释或代码块标记。\n"
        "情绪词请使用简短的中文词汇，例如：焦虑、疲惫、喜悦、平静、愤怒、孤独、尴尬等。\n\n"
        f"日记文本：{content}"
    )

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
        text = resp.json()["choices"][0]["message"]["content"].strip()
        
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        result = json.loads(text)
        
        if isinstance(result, list) and all(isinstance(x, str) for x in result):
            return result
        return None
    except Exception:
        
        return None


@router.post("/analyze_emotion")
def analyze_emotion(req: AnalyzeEmotionRequest):
    
    emotions = call_deepseek_emotions(req.content)
    if not emotions:
        emotions = ["平静"]
    return {"emotions": emotions}


def call_deepseek_analyze(content: str) -> dict | None:
    
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:  
        return None

    prompt = (
        "请分析下面这段日记文本，同时提取情绪词和事件词。\n"
        "1. 情绪词：文本中蕴含的情绪，用简短中文词汇表示，例如：烦躁、悲伤、喜悦、焦虑、平静、愤怒、孤独等。\n"
        "2. 事件词：可能影响情绪的具体行为或场景，例如：学习、工作、社交、运动、加班、旅行等。\n"
        "只返回一个 JSON 对象，不要输出任何多余的文字、解释或代码块标记。\n"
        '格式示例：{"emotions": ["烦躁", "悲伤"], "events": ["学习"]}\n\n'
        f"日记文本：{content}"
    )

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
        text = resp.json()["choices"][0]["message"]["content"].strip()
        
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        result = json.loads(text)
        
        if (
            isinstance(result, dict)
            and isinstance(result.get("emotions"), list)
            and all(isinstance(x, str) for x in result["emotions"])
            and isinstance(result.get("events"), list)
            and all(isinstance(x, str) for x in result["events"])
        ):
            return result
        return None
    except Exception:
        
        return None


@router.post("/analyze")
def analyze(req: AnalyzeEmotionRequest):
    
    result = call_deepseek_analyze(req.content)
    if not result:
        return {"emotions": [], "events": []}
    return {"emotions": result["emotions"], "events": result["events"]}