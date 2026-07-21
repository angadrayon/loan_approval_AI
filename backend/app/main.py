import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.applications import router as applications_router
from app.routers.predictions import router as predictions_router
from app.routers.admin import router as admin_router
from app.routers.reports import router as reports_router
from app.services.prediction_service import get_prediction_service
from app.services.shap_service import get_shap_service
from app.services.counterfactual_service import get_counterfactual_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup: Load ML models via PredictionService
    try:
        service = get_prediction_service()
        if service.xgb_model is not None:
            logger.info("PredictionService initialized — XGBoost model loaded")
        else:
            logger.warning("PredictionService initialized — XGBoost model NOT available")
        if service.rf_model is not None:
            logger.info("PredictionService initialized — Random Forest model loaded")
        else:
            logger.warning("PredictionService initialized — Random Forest model NOT available")
    except Exception as e:
        logger.error("Failed to initialize PredictionService: %s", e)

    # TODO: Initialize SHAP explainer with loaded XGBoost model (task 4.4)
    try:
        shap_svc = get_shap_service()
        if shap_svc.explainer is not None:
            logger.info("ShapExplainerService initialized — SHAP available")
        else:
            logger.warning("ShapExplainerService initialized — SHAP NOT available")
    except Exception as e:
        logger.error("Failed to initialize ShapExplainerService: %s", e)

    # TODO: Initialize DiCE engine with loaded XGBoost model (task 4.6)
    try:
        cf_svc = get_counterfactual_service()
        if cf_svc.xgb_model is not None:
            logger.info("CounterfactualService initialized — DiCE available")
        else:
            logger.warning("CounterfactualService initialized — DiCE NOT available")
    except Exception as e:
        logger.error("Failed to initialize CounterfactualService: %s", e)
    yield
    # Shutdown: Clean up resources
    # TODO: Release ML model resources if needed


app = FastAPI(
    title="AI Loan Decision Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Register routers
app.include_router(applications_router)
app.include_router(predictions_router)
app.include_router(admin_router)
app.include_router(reports_router)
