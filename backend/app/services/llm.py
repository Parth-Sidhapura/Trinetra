"""LLM provider abstraction: gemini | groq | ollama.

Switching the Hosted Demo Instance to the air-gapped variant is a config
change (LLM_PROVIDER=ollama), not a rewrite. Covers chat AND embeddings.
"""
import json
import logging
import re
from typing import Any

import httpx

from app.core.config import settings

log = logging.getLogger("trinetra.llm")


class LLMError(Exception):
    pass


def _extract_json(text: str) -> Any:
    """LLMs wrap JSON in prose/fences. Pull the payload out safely."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("[", "]"), ("{", "}")):
        s, e = text.find(opener), text.rfind(closer)
        if s != -1 and e > s:
            try:
                return json.loads(text[s:e + 1])
            except json.JSONDecodeError:
                continue
    raise LLMError(f"Could not parse JSON from model output: {text[:200]}")


# --------------------------------------------------------------- chat
def _gemini_chat(prompt: str, system: str | None, temperature: float) -> str:
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        settings.GEMINI_MODEL,
        system_instruction=system or None,
    )
    resp = model.generate_content(
        prompt, generation_config={"temperature": temperature}
    )
    return resp.text or ""


def _groq_chat(prompt: str, system: str | None, temperature: float) -> str:
    from groq import Groq
    client = Groq(api_key=settings.GROQ_API_KEY)
    msgs = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    resp = client.chat.completions.create(
        model=settings.GROQ_MODEL, messages=msgs, temperature=temperature
    )
    return resp.choices[0].message.content or ""


def _ollama_chat(prompt: str, system: str | None, temperature: float) -> str:
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system
    r = httpx.post(f"{settings.OLLAMA_BASE_URL}/api/generate",
                   json=payload, timeout=180)
    r.raise_for_status()
    return r.json().get("response", "")


def chat(prompt: str, *, system: str | None = None,
         temperature: float = 0.1, fallback: bool = True) -> str:
    """Primary provider, with automatic fallback to Groq if configured."""
    provider = settings.LLM_PROVIDER
    try:
        if provider == "gemini":
            return _gemini_chat(prompt, system, temperature)
        if provider == "groq":
            return _groq_chat(prompt, system, temperature)
        return _ollama_chat(prompt, system, temperature)
    except Exception as exc:  # noqa: BLE001
        log.warning("LLM provider %s failed: %s", provider, exc)
        if fallback and provider == "gemini" and settings.GROQ_API_KEY:
            log.info("Falling back to Groq")
            return _groq_chat(prompt, system, temperature)
        raise LLMError(str(exc)) from exc


def chat_json(prompt: str, *, system: str | None = None) -> Any:
    return _extract_json(chat(prompt, system=system, temperature=0.0))


# ---------------------------------------------------------- embeddings
def embed(text: str) -> list[float]:
    """768-dim embedding. Used for semantic entity resolution."""
    provider = settings.LLM_PROVIDER
    try:
        if provider in ("gemini", "groq"):   # groq has no embed API -> gemini
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            r = genai.embed_content(model=settings.GEMINI_EMBED_MODEL,
                                    content=text,
                                    task_type="semantic_similarity", output_dimensionality=768)
            return r["embedding"]
        r = httpx.post(f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                       json={"model": settings.OLLAMA_MODEL, "prompt": text},
                       timeout=60)
        r.raise_for_status()
        return r.json()["embedding"]
    except Exception as exc:  # noqa: BLE001
        log.warning("Embedding failed: %s", exc)
        return []


def provider_info() -> dict:
    return {
        "provider": settings.LLM_PROVIDER,
        "model": {
            "gemini": settings.GEMINI_MODEL,
            "groq": settings.GROQ_MODEL,
            "ollama": settings.OLLAMA_MODEL,
        }[settings.LLM_PROVIDER],
    }
