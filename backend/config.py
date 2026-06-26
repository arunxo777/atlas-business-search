"""Application configuration loaded from environment variables."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILES = (
    _ROOT / ".env",
    Path(__file__).resolve().parent / ".env",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(p) for p in _ENV_FILES if p.exists()] or ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Providers
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e2b"
    ollama_only: bool = False
    ollama_timeout_seconds: int = 180
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    mistral_api_key: str = ""
    mistral_model: str = "mistral-small-latest"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    serpapi_key: str = ""
    use_serpapi: bool = True
    use_omkar_google_scraper: bool = True
    use_rapidapi_google: bool = True
    rapidapi_google_key: str = ""
    google_scraper_max_results: int = 20
    use_firecrawl: bool = True
    firecrawl_api_key: str = ""
    firecrawl_api_url: str = "https://api.firecrawl.dev"
    firecrawl_search_limit: int = 15

    # Proxy pool — https://github.com/naiba/proxy-in-a-box
    use_proxy_pool: bool = True
    proxy_pool_http: str = "http://127.0.0.1:8080"
    proxy_pool_https: str = "http://127.0.0.1:8081"
    proxy_pool_api: str = "http://127.0.0.1:8083"

    # App
    database_url: str = "sqlite+aiosqlite:///./data/research.db"
    cache_ttl_hours: int = 24
    max_concurrent_scrapers: int = 10
    max_businesses_per_query: int = 500
    backend_port: int = 8000
    frontend_port: int = 3000
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlite_path(self) -> str:
        url = self.database_url
        if url.startswith("sqlite+aiosqlite:///"):
            path = url.replace("sqlite+aiosqlite:///", "")
            if path.startswith("./"):
                return path[2:]
            return path
        return "./data/research.db"

    def provider_configs(self) -> list[dict[str, str]]:
        configs = [
            {
                "name": "ollama",
                "model": f"ollama/{self.ollama_model}",
                "api_base": self.ollama_base_url,
            },
        ]
        if self.ollama_only:
            return configs
        configs.extend(
            [
                {
                    "name": "groq",
                    "model": f"groq/{self.groq_model}",
                    "api_key": self.groq_api_key,
                },
                {
                    "name": "mistral",
                    "model": f"mistral/{self.mistral_model}",
                    "api_key": self.mistral_api_key,
                },
                {
                    "name": "openai",
                    "model": self.openai_model,
                    "api_key": self.openai_api_key,
                },
            ]
        )
        return configs

    async def _probe_ollama(self) -> dict[str, str] | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.ollama_base_url.rstrip('/')}/api/tags")
                if resp.status_code != 200:
                    return None
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                target = self.ollama_model
                if target not in models:
                    base_name = target.split(":")[0]
                    matching = [m for m in models if m.startswith(base_name)]
                    if not matching:
                        logger.warning("Ollama running but model %s not found", target)
                        return None
                    target = matching[0]
                return {
                    "name": "ollama",
                    "model": f"ollama/{target}",
                    "api_base": self.ollama_base_url,
                }
        except Exception as exc:
            logger.debug("Ollama probe failed: %s", exc)
            return None

    async def _probe_litellm_provider(self, cfg: dict[str, str]) -> dict[str, str] | None:
        api_key = cfg.get("api_key", "")
        if not api_key:
            return None
        try:
            import litellm
            from litellm.exceptions import AuthenticationError

            kwargs: dict[str, Any] = {
                "model": cfg["model"],
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
                "api_key": api_key,
            }
            await litellm.acompletion(**kwargs)
            return {"name": cfg["name"], "model": cfg["model"], "api_key": api_key}
        except Exception as exc:
            exc_name = type(exc).__name__
            if "Authentication" in exc_name or "Auth" in exc_name:
                logger.debug("%s auth failed", cfg["name"])
            else:
                logger.debug("%s probe failed: %s", cfg["name"], exc)
            return None

    async def get_active_llm_provider(self, force: str | None = None) -> dict[str, Any]:
        """Probe providers in priority order and return the first available."""
        if force and force != "auto":
            for cfg in self.provider_configs():
                if cfg["name"] == force:
                    if cfg["name"] == "ollama":
                        result = await self._probe_ollama()
                        if result:
                            return result
                    else:
                        result = await self._probe_litellm_provider(cfg)
                        if result:
                            return result
                    raise RuntimeError(f"Forced provider '{force}' is not available")

        if self.ollama_only:
            ollama = await self._probe_ollama()
            if ollama:
                return ollama
            raise RuntimeError(
                "Ollama is required (OLLAMA_ONLY=true) but is not running. "
                "Start Ollama and pull your model: ollama pull gemma2:2b"
            )

        ollama = await self._probe_ollama()
        if ollama:
            return ollama

        for cfg in self.provider_configs()[1:]:
            result = await self._probe_litellm_provider(cfg)
            if result:
                return result

        raise RuntimeError(
            "No LLM provider available. Install Ollama locally or configure API keys."
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
