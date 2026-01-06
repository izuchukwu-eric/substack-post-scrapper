"""Configuration settings for Substack Scraper."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Browser settings
    headless: bool = Field(default=True, description="Run browser in headless mode")

    # Scraping limits
    default_results_limit: int = Field(default=50, description="Default posts per keyword")
    max_results_limit: int = Field(default=200, description="Maximum posts per keyword")
    scroll_delay_ms: int = Field(default=1000, description="Delay between scrolls in ms")
    scroll_timeout_ms: int = Field(default=30000, description="Max time waiting for new content")

    # Rate limiting
    rate_limit_requests: int = Field(default=10, description="Requests per time window")
    rate_limit_window_seconds: int = Field(default=60, description="Time window in seconds")

    # Output settings
    output_dir: str = Field(default="./output", description="JSON output directory")

    # API settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    model_config = {
        "env_prefix": "SUBSTACK_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# Global settings instance
settings = Settings()
