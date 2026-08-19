"""
Cadena de LLMs con fallback
===========================

Replica el patrón de ``dev/ds`` (``src/providers/llm.ts``): se prueban los
proveedores OpenAI-compatible en orden de prioridad (``LLM1..LLM8``) y se usa
el primero que responda. Ante error HTTP, timeout o respuesta vacía, se pasa
al siguiente proveedor. Si todos fallan, retorna ``None``.

Sin dependencias de ``openai``: habla directo con ``/chat/completions`` vía
``httpx`` (ya en requirements). Temperatura 0 y timeout por defecto, igual que
el original.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 60.0


class LLMError(RuntimeError):
    """Error genérico de la cadena de LLMs."""


def chat_completion(
    messages: List[Dict[str, Any]],
    *,
    providers: Optional[List[dict]] = None,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Optional[str]:
    """Envía los mensajes a la cadena de LLMs y devuelve el primer texto útil.

    Args:
        messages: Mensajes estilo OpenAI (``role`` + ``content``).
        providers: Lista ordenada de providers; por defecto usa
            ``settings.llm_providers()``.
        temperature: Temperatura de muestreo (por defecto 0, determinista).
        max_tokens: Límite de tokens de la respuesta (opcional).
        timeout: Timeout por proveedor en segundos.

    Returns:
        El contenido del primer proveedor que responda, o ``None`` si todos
        fallan.
    """
    chain = providers if providers is not None else settings.llm_providers()
    if not chain:
        logger.warning("Sin proveedores LLM configurados (LLM1_*..LLM8_* o DEEPSEEK_API_KEY)")
        return None

    payload: Dict[str, Any] = {
        "model": "",  # se completa por proveedor
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    last_error: Optional[Exception] = None
    for provider in chain:
        model = provider.get("model", "")
        base_url = (provider.get("base_url") or "").rstrip("/")
        url = f"{base_url}/chat/completions"
        try:
            payload["model"] = model
            resp = httpx.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {provider.get('api_key', '')}",
                },
                json=payload,
                timeout=timeout,
            )
            if not resp.is_success:
                logger.warning(
                    "[llm:%s] HTTP %s: %s", model, resp.status_code,
                    resp.text[:200],
                )
                continue
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            if content:
                return content
            logger.warning("[llm:%s] respuesta vacía", model)
        except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError) as exc:
            last_error = exc
            logger.warning("[llm:%s] %s", model, exc)
        except Exception as exc:  # noqa: BLE001 - no tumbar la cadena
            last_error = exc
            logger.warning("[llm:%s] %s", model, exc)

    raise LLMError("Todos los proveedores LLM fallaron") from last_error


def summarize(
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int = 300,
    **kwargs: Any,
) -> Optional[str]:
    """Atajo para obtener un resumen narrativo de la cadena de LLMs.

    Args:
        system_prompt: Instrucciones de rol.
        user_prompt: Contenido a resumir.
        max_tokens: Límite de tokens de la respuesta.
        **kwargs: Pasados a :func:`chat_completion` (providers, temperature...).

    Returns:
        El texto del resumen o ``None`` si la cadena falla.
    """
    try:
        return chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            **kwargs,
        )
    except LLMError:
        return None