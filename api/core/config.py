from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Quila API"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 60

    # Database
    DATABASE_URL: str
    
    # iCalendar
    DOMAIN: str = "example.com"

    # Chatbot integration (/bot/*). Empty key = bot endpoints disabled.
    BOT_API_KEY: str = ""
    # Lifetime of a chatbot hold (TENTATIVE booking) before it expires lazily
    HOLD_TTL_HOURS: int = 24
    # IANA timezone that defines the business "today" (check-in dates, current prices)
    BUSINESS_TIMEZONE: str = "America/Argentina/Buenos_Aires"

    class Config:
        case_sensitive = True

settings = Settings()
