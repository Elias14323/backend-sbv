"""Helpers for interacting with the Mistral AI API."""

from __future__ import annotations

from functools import lru_cache

from mistralai import Mistral

from .config import settings


@lru_cache(maxsize=1)
def get_mistral_client() -> Mistral:
    """Return a singleton Mistral client configured from settings."""

    api_key = settings.mistral_api_key
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY must be set to use embeddings")
    return Mistral(api_key=api_key)


__all__ = ["get_mistral_client"]
