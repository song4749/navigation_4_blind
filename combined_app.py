from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from fast_api.detection_router import router as detection_router
from navigation_app.navigation_router import router as navigation_router

from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pathlib import Path

app = FastAPI(title="시각장애인 내비게이션 통합 시스템")

# ✅ CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 정적 파일 및 템플릿 설정
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "navigation_app" / "static"
TEMPLATES_DIR = BASE_DIR / "navigation_app" / "templates"
AUDIO_DIR = BASE_DIR / "fast_api" / "mp3"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/static_audio", StaticFiles(directory=AUDIO_DIR), name="static_audio")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# ✅ JavaScript 모듈 지원을 위한 헤더 설정
@app.middleware("http")
async def add_js_header(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.endswith(".js"):
        response.headers["Content-Type"] = "application/javascript"
    return response

# ✅ 각 기능별 라우터 등록
app.include_router(detection_router)
app.include_router(navigation_router)

# ✅ 기본 루트 페이지 연결
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
