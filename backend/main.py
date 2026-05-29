import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Adjust path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from database import engine, Base
from ml_service import ml_service
from routers import dashboard, dealers, transactions, investigations, upload, farmers

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AgriShield Fraud Monitoring API",
    version="1.0.0",
    description="Agricultural Subsidy Fraud Detection — REST API",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
CORS_ORIGINS = [o.strip() for o in _origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API Key middleware  (dev-friendly: disabled when API_KEY is not set)
# ---------------------------------------------------------------------------
_API_KEY = os.getenv("API_KEY", "")

# Routes that never require auth
_PUBLIC_PREFIXES = ("/docs", "/redoc", "/openapi.json", "/healthz")


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Dev mode — key not configured, allow everything
        if not _API_KEY:
            return await call_next(request)
        # Always allow Swagger / health
        if any(request.url.path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)
        # Allow CORS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)
            
        # Check header
        key = request.headers.get("X-API-Key", "")
        if key != _API_KEY:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid or missing API key. Set X-API-Key header."},
            )
        return await call_next(request)


app.add_middleware(APIKeyMiddleware)

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    # Auto-create all tables (idempotent)
    Base.metadata.create_all(bind=engine)
    print("[DB] Tables ensured.")

    model_path = Path(os.getenv(
        "MODEL_PATH",
        Path(__file__).parent.parent / "models" / "fraud_detector.pkl"
    ))
    ml_service.load(model_path)


# ---------------------------------------------------------------------------
# Health check (public)
# ---------------------------------------------------------------------------
@app.get("/healthz", tags=["meta"])
def health():
    return {
        "status": "ok",
        "model_loaded": ml_service.is_loaded,
        "model_auc": ml_service.metrics.get("roc_auc") if ml_service.is_loaded else None,
    }


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(dashboard.router)
app.include_router(dealers.router)
app.include_router(transactions.router)
app.include_router(investigations.router)
app.include_router(upload.router)
app.include_router(farmers.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)