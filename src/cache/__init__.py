"""Cache Manager — Gestión centralizada de caché de datos."""
from src.cache.manager import (
    download_pdf,
    process_and_save_ocr,
    cache_api_response,
    get_cached_api,
    get_cache_stats,
    gc_cache,
    is_downloaded,
    is_ocr_processed,
)

__all__ = [
    "download_pdf",
    "process_and_save_ocr",
    "cache_api_response",
    "get_cached_api",
    "get_cache_stats",
    "gc_cache",
    "is_downloaded",
    "is_ocr_processed",
]
