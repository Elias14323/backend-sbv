"""Main FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_stream, routes_topics
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events."""
    # Startup
    print("🚀 Starting Backend SBV API...")
    yield
    # Shutdown
    print("👋 Shutting down Backend SBV API...")


app = FastAPI(
    title="Backend SBV - News Clustering API",
    description="API for news aggregation, clustering, and debiasing",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes_topics.router, prefix="/api/v1")
app.include_router(routes_stream.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Backend SBV API",
        "docs": "/docs",
        "version": "0.1.0",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
