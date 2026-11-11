from collections import defaultdict, deque
from time import monotonic

from pathlib import Path
import sys

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine, ensure_compatible_schema
from .routes import router

settings = get_settings()
Base.metadata.create_all(bind=engine)
ensure_compatible_schema()

app = FastAPI(title="StudyFlow API", version="0.1.0", docs_url="/api/docs", redoc_url="/api/redoc")
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])
app.include_router(router)

if getattr(sys, "frozen", False):
    frontend_dist = Path(sys._MEIPASS) / "frontend" / "dist"
else:
    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def frontend():
        return FileResponse(frontend_dist / "index.html")

_rate_window: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def auth_rate_limit(request: Request, call_next):
    if request.method == "POST" and request.url.path in {"/api/v1/auth/login", "/api/v1/auth/register"}:
        key = request.client.host if request.client else "unknown"
        now = monotonic(); attempts = _rate_window[key]
        while attempts and now - attempts[0] > 60: attempts.popleft()
        if len(attempts) >= 10:
            return JSONResponse(status_code=429, content={"detail": "Muitas tentativas. Aguarde um minuto."})
        attempts.append(now)
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
