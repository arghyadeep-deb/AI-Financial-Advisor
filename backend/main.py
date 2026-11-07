# ── Load .env FIRST before anything else ─────────────────────────────────────
import logging
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

# ── Add project root to Python path ──────────────────────────────────────────
# This ensures all root-level folders (agents, engines, rag, etc.)
# are importable from anywhere in the project
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Windows consoles default to cp1252; never let a log/print crash a request.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core import errors
from backend.core.config import config

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("advisor")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Refuse unsafe production configuration before serving anything.
    config.validate()
    if config._ephemeral_key:
        log.warning("SECRET_KEY not set: using an ephemeral per-process key (tokens expire on restart). "
                    "Never do this outside local development.")
    from backend.core.database import init_db
    state = init_db()
    log.info("database ready (schema %s)", (state or {}).get("current") or (state or {}).get("after", {}).get("current"))
    yield


app = FastAPI(
    title="AI Financial Advisor API",
    description="Intelligent financial advisory platform for Indian investors",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,           # explicit origins; never "*" with credentials
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "Retry-After"],
)
errors.install(app)


@app.get("/health", tags=["System"])
def health():
    """Liveness only: no database, provider or secret details."""
    return {"status": "ok", "service": "AI Financial Advisor API", "version": app.version}


from backend.controllers.auth_controller import router as auth_router          # noqa: E402
from backend.controllers.profile_controller import router as profile_router    # noqa: E402
from backend.controllers.analysis_controller import router as analysis_router  # noqa: E402
from backend.controllers.chat_controller import router as chat_router          # noqa: E402
from backend.controllers.thread_controller import router as thread_router      # noqa: E402

app.include_router(auth_router)
app.include_router(__import__('backend.controllers.mfa_controller', fromlist=['router']).router)
app.include_router(profile_router)
app.include_router(analysis_router)
app.include_router(chat_router)
app.include_router(thread_router)


@app.get("/")
def root():
    return {"message": "AI Financial Advisor API is running"}
app.include_router(__import__("backend.controllers.platform_controller", fromlist=["router"]).router)
app.include_router(__import__("backend.controllers.statement_controller", fromlist=["router"]).router)
app.include_router(__import__("backend.controllers.planning_controller", fromlist=["router"]).router)
app.include_router(__import__("backend.controllers.education_controller", fromlist=["router"]).router)
app.include_router(__import__("backend.controllers.portfolio_controller", fromlist=["router"]).router)
app.include_router(__import__("backend.controllers.tax_controller", fromlist=["router"]).router)
app.include_router(__import__("backend.controllers.household_controller", fromlist=["router"]).router)
app.include_router(__import__("backend.controllers.transaction_controller", fromlist=["router"]).router)
app.include_router(__import__("backend.controllers.pilot_controller", fromlist=["router"]).router)
app.include_router(__import__("backend.controllers.support_controller", fromlist=["router"]).router)


# ── Web UI: plain HTML/CSS/JS served from frontend/static (no build step) ────
from fastapi import Request                                # noqa: E402
from fastapi.staticfiles import StaticFiles               # noqa: E402

_STATIC_DIR = os.path.join(ROOT_DIR, "frontend", "static")
_UI_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
           "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")


@app.middleware("http")
async def ui_security_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/app" or request.url.path.startswith("/app/"):
        response.headers["Content-Security-Policy"] = _UI_CSP     # scoped: Swagger/ReDoc keep working
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-cache"
    return response


if os.path.isdir(_STATIC_DIR):
    app.mount("/app", StaticFiles(directory=_STATIC_DIR, html=True), name="web-ui")
