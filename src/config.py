import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    app_name: str = "CareerPilot AI"
    log_level: str = "INFO"
    minimum_match_threshold: float = Field(default=70.0, description="Minimum ATS match score to proceed")
    
    # Primary Free AI Providers (Groq & Hugging Face)
    groq_api_key: str = Field(default="", env="GROQ_API_KEY")
    groq_model_name: str = "llama-3.3-70b-versatile"
    huggingface_api_key: str = Field(default="", env="HUGGINGFACE_API_KEY")
    
    # Optional Fallback Providers
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model_name: str = "gpt-4o"
    cartesia_api_key: Optional[str] = Field(default=None, env="CARTESIA_API_KEY")
    
    # Proxies & Webhooks
    residential_proxy_url: str = Field(default="", env="RESIDENTIAL_PROXY_URL")
    hitl_webhook_url: str = Field(default="", env="HITL_WEBHOOK_URL")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
