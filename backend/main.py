from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import models  
from database import Base, engine
from routers import auth, emotion, library, logs, preferences, recommend, recommendations, report, schedules, stats, tags


Base.metadata.create_all(bind=engine)


models.init_db()


models.init_default_tags()


app = FastAPI(title="Mood Guardian API", docs_url=None, redoc_url=None)



allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="",  
    )


app.include_router(auth.router)
app.include_router(emotion.router)
app.include_router(library.router)
app.include_router(logs.router)
app.include_router(stats.router)
app.include_router(report.router)
app.include_router(recommend.router)
app.include_router(recommendations.router)
app.include_router(preferences.router)
app.include_router(schedules.router)
app.include_router(tags.router)


@app.get("/")
def read_root():
    return {"message": "Hello World"}