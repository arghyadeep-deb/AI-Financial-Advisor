from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.database import init_db
from backend.controllers.auth_controller     import router as auth_router
from backend.controllers.profile_controller  import router as profile_router
from backend.controllers.analysis_controller import router as analysis_router
from backend.controllers.chat_controller     import router as chat_router
from backend.controllers.thread_controller   import router as thread_router


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "AI Financial Advisor API",
    description = "Intelligent financial advisory platform for Indian investors",
    version     = "1.0.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"]
)


# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    print("[API] Starting AI Financial Advisor...")
    init_db()
    print("[API] Ready ✓")


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(analysis_router)
app.include_router(chat_router)
app.include_router(thread_router)


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    """Check if API is running."""
    return {
        "status":  "ok",
        "service": "AI Financial Advisor API",
        "version": "1.0.0"
    }