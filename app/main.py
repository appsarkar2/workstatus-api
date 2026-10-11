# backend/app/main.py
import logging
import time
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth import router as auth_router
from app.blocks import register_all_blocks
from app.blocks.registry import list_active_blocks
from app.auth import get_current_user
from app.settings import settings
from fastapi import Depends


# ---- Logging setup ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("workstatus")


# ---- App ----
app = FastAPI(title="WorkStatus API", version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Request logging middleware ----
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.0f}ms)"
    )
    return response


# ---- Global exception handler ----
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__,
            "path": str(request.url.path),
        },
    )


# ---- Routes ----
app.include_router(auth_router)
register_all_blocks(app)


@app.get("/")
def root():
    return {"status": "ok", "service": "workstatus-api"}


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "healthy"}


@app.get("/version")
def version():
    return {
        "version": settings.app_version,
        "environment": settings.environment,
        "service": "workstatus-api",
    }


@app.get("/api/blocks")
def get_blocks(current=Depends(get_current_user)):
    return {"blocks": list_active_blocks()}