"""FastAPI application entry point"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.phi_redaction import PHIRedactingFormatter, sanitize_error_message
from app.api.routes import auth, encounters, audit

# Configure logging with PHI redaction
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[logging.StreamHandler()],
)

# Apply PHI redacting formatter to all handlers
for handler in logging.root.handlers:
    if handler.formatter:
        handler.setFormatter(PHIRedactingFormatter(handler.formatter._fmt))
    else:
        handler.setFormatter(PHIRedactingFormatter(log_format))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger = logging.getLogger(__name__)
    logger.info("Starting HIPAA Encounter API")
    yield
    # Shutdown
    logger.info("Shutting down HIPAA Encounter API")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="HIPAA-Compliant Patient Encounter API with PHI redaction and audit trails",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom validation error handler that sanitizes error messages.
    """
    errors = exc.errors()
    sanitized_errors = []
    
    for error in errors:
        # Redact any PHI that might be in error messages
        error_msg = str(error.get("msg", ""))
        sanitized_msg = sanitize_error_message(error_msg)
        
        sanitized_error = {
            "loc": error.get("loc"),
            "msg": sanitized_msg,
            "type": error.get("type"),
        }
        sanitized_errors.append(sanitized_error)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": sanitized_errors},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    General exception handler that prevents information leakage.
    """
    logger = logging.getLogger(__name__)
    error_msg = "An internal error occurred"
    safe_msg = sanitize_error_message(error_msg, {"error_type": type(exc).__name__})
    
    logger.error("Unhandled exception: %s", safe_msg, exc_info=exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": safe_msg},
    )


# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(encounters.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "message": "HIPAA Encounter API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}
