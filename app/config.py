"""
Configuration settings for Auto-QA PR Sentinel System.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PR_QA_")

    APP_NAME: str = "Auto-QA PR Sentinel"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Orchestrator & Repair Loop
    MAX_REPAIR_RETRIES: int = 3
    RETRY_BACKOFF_SECONDS: float = 0.5
    
    # Sandbox Settings
    SANDBOX_MODE: Literal["auto", "subprocess", "docker"] = "auto"
    SANDBOX_TIMEOUT_SECONDS: int = 15
    SANDBOX_DOCKER_IMAGE: str = "python:3.13-slim"

    # Worker Pool & Scalability
    WORKER_CONCURRENCY: int = 4
    TASK_QUEUE_MAX_SIZE: int = 100

    # RAG Settings
    RAG_TOP_K: int = 3
    RAG_SIMILARITY_THRESHOLD: float = 0.35

    # Software Quality Thresholds
    MIN_TEST_COVERAGE_PERCENT: float = 85.0
    MIN_RELIABILITY_INDEX: float = 80.0
    MAX_ACCEPTABLE_CYCLOMATIC_COMPLEXITY: int = 10

settings = Settings()
