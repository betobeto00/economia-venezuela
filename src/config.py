"""
Configuración del sistema de Economía Venezuela
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración principal del sistema"""
    
    # Application
    APP_NAME: str = "Economía Venezuela"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/economia_ve"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # API Keys
    BCV_API_KEY: Optional[str] = None
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_API_SECRET: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None
    
    # Reddit API
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "EconomiaVenezuela/0.1.0"
    
    # Twitter API
    TWITTER_BEARER_TOKEN: Optional[str] = None
    
    # Scheduling (in minutes/hours)
    DOLLAR_COLLECT_INTERVAL_MINUTES: int = 5
    NEWS_COLLECT_INTERVAL_HOURS: int = 6
    SENTIMENT_ANALYSIS_HOUR: int = 22
    WEEKLY_REPORT_DAY: str = "sunday"
    WEEKLY_REPORT_HOUR: int = 8
    
    # Google (Encuestas - Fase B)
    GOOGLE_CREDENTIALS_PATH: Optional[str] = None
    SURVEY_COLLECT_INTERVAL_MINUTES: int = 60
    SURVEY_QUALITY_THRESHOLD: float = 0.5
    # IDs de formularios y hojas vinculadas (por segmento)
    SURVEY_PERSONA_COMUN_FORM_ID: Optional[str] = None
    SURVEY_PERSONA_COMUN_SHEET_ID: Optional[str] = None
    SURVEY_COMERCIANTE_FORM_ID: Optional[str] = None
    SURVEY_COMERCIANTE_SHEET_ID: Optional[str] = None

    # Fase A - Fuentes de datos (URLs configurables para tests/fallback)
    BCV_RATE_API_URL: str = "https://ve.dolarapi.com/v1/dolares/oficial"
    BCV_IPC_API_URL: str = "https://api.bcv.org.ve/ipc"
    OVF_BASE_URL: str = "https://observatoriodefinanzas.com"
    WORLD_BANK_API_URL: str = "https://api.worldbank.org/v2"
    ONAPRE_BASE_URL: str = "https://www.onapre.gob.ve"
    CGR_BASE_URL: str = "https://www.cgr.gob.ve"
    INE_BASE_URL: str = "https://www.ine.gob.ve"
    OPEC_BASE_URL: str = "https://www.opec.org"
    BINANCE_P2P_URL: str = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    # Feeds RSS de noticias (separados por coma)
    RSS_FEEDS: str = (
        "https://elpitazo.net/feed,"
        "https://www.bancaynegocios.com/feed/,"
        "https://efectococuyo.com/feed/"
    )
    
    # Dashboard
    DASHBOARD_PORT: int = 8501
    API_PORT: int = 8000
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # API Rate Limits
    BCV_RATE_LIMIT: int = 100  # requests per hour
    BINANCE_RATE_LIMIT: int = 1200  # requests per minute
    NEWS_API_RATE_LIMIT: int = 100  # requests per day
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Ignorar variables de entorno ajenas al sistema (p.ej. CONTEXT7_API_KEY)
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Obtiene la configuración cacheada.
    
    Returns:
        Settings: Instancia de configuración
    """
    return Settings()


settings = get_settings()
