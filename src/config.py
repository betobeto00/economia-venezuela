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

    # Cadena de LLMs con fallback (LLM1..LLM8, en orden de prioridad).
    # Se prueban en secuencia; el primero que responda se usa (mismo patrón
    # que dev/ds: OpenRouter → OmniRoute → Z.AI → Gemini).
    LLM1_API_KEY: Optional[str] = None
    LLM1_BASE_URL: Optional[str] = None
    LLM1_MODEL: Optional[str] = None
    LLM2_API_KEY: Optional[str] = None
    LLM2_BASE_URL: Optional[str] = None
    LLM2_MODEL: Optional[str] = None
    LLM3_API_KEY: Optional[str] = None
    LLM3_BASE_URL: Optional[str] = None
    LLM3_MODEL: Optional[str] = None
    LLM4_API_KEY: Optional[str] = None
    LLM4_BASE_URL: Optional[str] = None
    LLM4_MODEL: Optional[str] = None
    LLM5_API_KEY: Optional[str] = None
    LLM5_BASE_URL: Optional[str] = None
    LLM5_MODEL: Optional[str] = None
    LLM6_API_KEY: Optional[str] = None
    LLM6_BASE_URL: Optional[str] = None
    LLM6_MODEL: Optional[str] = None
    LLM7_API_KEY: Optional[str] = None
    LLM7_BASE_URL: Optional[str] = None
    LLM7_MODEL: Optional[str] = None
    LLM8_API_KEY: Optional[str] = None
    LLM8_BASE_URL: Optional[str] = None
    LLM8_MODEL: Optional[str] = None
    
    # Reddit API (opcional; JSON público funciona sin credenciales)
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "EconomiaVenezuela/0.1.0"

    # Zernio (fallback de pago para Reddit, como Automaton)
    ZERNIO_API_KEY: Optional[str] = None

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

    # Fase A - Recolección de mercado
    MARKET_COLLECT_INTERVAL_MINUTES: int = 30

    # Fase A - Fuentes de datos (URLs configurables para tests/fallback)
    BCV_RATE_API_URL: str = "https://ve.dolarapi.com/v1/dolares/oficial"
    BCV_IPC_API_URL: str = "https://api.bcv.org.ve/ipc"
    OVF_BASE_URL: str = "https://observatoriodefinanzas.com"
    WORLD_BANK_API_URL: str = "https://api.worldbank.org/v2"
    ONAPRE_BASE_URL: str = "https://www.onapre.gob.ve"
    CGR_BASE_URL: str = "https://www.cgr.gob.ve"
    INE_BASE_URL: str = "https://www.ine.gob.ve"
    OPEC_BASE_URL: str = "https://www.opec.org"
    SENIAT_BASE_URL: str = "https://www.seniat.gob.ve"
    MPPEF_BASE_URL: str = "https://www.mppef.gob.ve"
    PDVSA_BASE_URL: str = "https://pdvsa-adhoc.com"
    IMF_SDMX_URL: str = "https://dataservices.imf.org/REST/SDMX_JSON.svc"
    CEPALSTAT_BASE_URL: str = "https://api-cepalstat.cepal.org/cepalstat/api/v1"
    UNSCEB_BASE_URL: str = "https://unsceb.org"
    GACETA_OFICIAL_BASE_URL: str = "http://www.gacetaoficial.gob.ve"
    AN_BASE_URL: str = "https://www.asambleanacional.gob.ve"
    BINANCE_P2P_URL: str = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    # Feeds RSS de noticias (separados por coma)
    # Nota: elpitazo.net y bancaynegocios.com no responden desde la red local
    # (geo-block/WAF); guia.com.ve es un directorio feedburner descontinuado.
    # Vivos: Diario Las Américas, El Tiempo (economía) y el staging de Efecto
    # Cocuyo (economía) y Primicia (general).
    RSS_FEEDS: str = (
        "https://www.diariolasamericas.com/rss/pages/venezuela.xml,"
        "https://www.diariolasamericas.com/rss/pages/mundo.xml,"
        "https://efectococuyo-np.newspackstaging.com/economia/feed/,"
        "https://www.eltiempo.com/rss/economia.xml,"
        "https://primicia.com.ve/feed/"
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

    def llm_providers(self) -> list[dict]:
        """Proveedores LLM en orden de prioridad (LLM1..LLM8).

        Cada proveedor que tenga las 3 variables (api_key, base_url, model) se
        incluye. Si no hay ningún LLM_N configurado, cae a ``DEEPSEEK_API_KEY``
        como único proveedor (compatibilidad con versiones anteriores).

        Returns:
            Lista de dicts ``{"api_key", "base_url", "model"}`` en orden.
        """
        providers: list[dict] = []
        for i in range(1, 9):
            api_key = getattr(self, f"LLM{i}_API_KEY", None)
            base_url = getattr(self, f"LLM{i}_BASE_URL", None)
            model = getattr(self, f"LLM{i}_MODEL", None)
            if api_key and base_url and model:
                providers.append({"api_key": api_key, "base_url": base_url, "model": model})
        if not providers and self.DEEPSEEK_API_KEY:
            providers.append({
                "api_key": self.DEEPSEEK_API_KEY,
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-chat",
            })
        return providers


@lru_cache()
def get_settings() -> Settings:
    """
    Obtiene la configuración cacheada.
    
    Returns:
        Settings: Instancia de configuración
    """
    return Settings()


settings = get_settings()
