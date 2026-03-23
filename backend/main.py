# ── Load .env FIRST before anything else ─────────────────────────────────────
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ── Add project root to Python path ──────────────────────────────────────────
# This ensures all root-level folders (agents, engines, rag, etc.)
# are importable from anywhere in the project
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ── Now import FastAPI ────────────────────────────────────────────────────────
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# ─── Create App ───────────────────────────────────────────────────────────────

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
    from backend.core.database import init_db
    init_db()
    print("[API] Ready ✓")


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    """Check if API is running."""
    return {
        "status":  "ok",
        "service": "AI Financial Advisor API",
        "version": "1.0.0"
    }


# ─── Include Routers ──────────────────────────────────────────────────────────
# Imported after app is created to avoid circular import issues

from backend.controllers.auth_controller     import router as auth_router
from backend.controllers.profile_controller  import router as profile_router
from backend.controllers.analysis_controller import router as analysis_router
from backend.controllers.chat_controller     import router as chat_router
from backend.controllers.thread_controller   import router as thread_router

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(analysis_router)
app.include_router(chat_router)
app.include_router(thread_router)