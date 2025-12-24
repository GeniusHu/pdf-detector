#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration settings for PDF similarity detection service
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Application
    app_name: str = "PDF Similarity Detection API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")

    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    reload: bool = Field(default=True, env="RELOAD")

    # File storage
    upload_dir: str = Field(default="uploads", env="UPLOAD_DIR")
    export_dir: str = Field(default="exports", env="EXPORT_DIR")
    max_file_size: int = Field(default=100 * 1024 * 1024, env="MAX_FILE_SIZE")  # 100MB
    allowed_extensions: list = [".pdf"]

    # PDF processing
    max_sequences: int = Field(default=5000, env="MAX_SEQUENCES")
    min_similarity: float = Field(default=0.75, env="MIN_SIMILARITY")
    default_processing_mode: str = Field(default="fast", env="PROCESSING_MODE")
    max_processes: int = Field(default=os.cpu_count() or 4, env="MAX_PROCESSES")
    context_chars: int = Field(default=100, env="CONTEXT_CHARS")

    # Security
    jwt_secret: str = Field(default="your-secret-key", env="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # Redis (for future caching)
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", env="LOG_FILE")

    # CORS
    cors_origins: list = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        env="CORS_ORIGINS"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def redis_settings(self) -> dict:
        """Get Redis connection settings"""
        if self.redis_url:
            return {"url": self.redis_url}
        return {
            "host": self.redis_host,
            "port": self.redis_port,
            "db": self.redis_db,
            "decode_responses": True
        }

    @property
    def upload_path(self) -> str:
        """Get absolute upload path"""
        return os.path.abspath(self.upload_dir)

    @property
    def export_path(self) -> str:
        """Get absolute export path"""
        return os.path.abspath(self.export_dir)

    def create_directories(self):
        """Create necessary directories"""
        os.makedirs(self.upload_path, exist_ok=True)
        os.makedirs(self.export_path, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)


# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get application settings (dependency injection)"""
    return settings