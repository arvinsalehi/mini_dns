"""
Forked from https://github.com/purijs/fastapi-best-practices

Auto Documented by claude-sonnet-3.7

Main application module for the Mini DNS Service.

This module initializes and configures the FastAPI application with all necessary
middleware, routers, and settings. It serves as the entry point for the DNS service.
"""

from fastapi import FastAPI
from app.routers.dns import router as dns_router
from app.middleware.correlation_id import CorrelationIdMiddleware
from app.core.security import add_cors

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    This function:
    1. Initializes the FastAPI application
    2. Includes the DNS router
    3. Adds middleware for request tracking
    4. Configures CORS settings
    5. Sets up health check endpoint
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    
    app = FastAPI(title="User API")

    # Include routers
    app.include_router(dns_router)

    # Add middleware for request tracking
    app.add_middleware(CorrelationIdMiddleware)

    # Configure CORS settings
    add_cors(app)

    # Debug ENV
    # if settings.DEBUG:
    #     logger.info("Running in debug mode")
    
    @app.get("/healthcheck")
    async def healthcheck():
        """
        Health check endpoint to verify service status.
        
        Returns:
            dict: Status message indicating service health
        """
        return {"status": "ok"}
    
    return app

# Initialize the application
app = create_app()
