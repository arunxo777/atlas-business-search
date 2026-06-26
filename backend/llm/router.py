"""LiteLLM multi-provider router with automatic fallback chain."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import httpx
import litellm
from tenacity import retry, stop_after_attempt, wait_exponential

from config import Settings, get_settings

logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True


class LLMRouter:
    PROVIDER_ORDER = ["ollama", "groq", "mistral", "openai"]

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.active_provider: dict[str, Any] | None = None
        self.available_providers: list[str] = []
        self.last_latency_ms: float | None = None
        self._initialized = False
        self._locked_provider: str | None = None

    def _provider_order(self) -> list[str]:
        if self.settings.ollama_only:
            return ["ollama"]
        return self.PROVIDER_ORDER

    async def initialize(self, force_provider: str | None = None) -> None:
        order = self._provider_order()
        self.available_providers = []
        for name in order:
            cfg = await self._probe_provider(name)
            if cfg:
                self.available_providers.append(name)

        if force_provider and force_provider != "auto":
            cfg = await self._probe_provider(force_provider)
            if cfg:
                self.active_provider = cfg
                self._locked_provider = force_provider
            else:
                raise RuntimeError(f"Provider '{force_provider}' is not available")
        elif self.available_providers:
            self.active_provider = await self._probe_provider(
                self.available_providers[0]
            )
            if self.settings.ollama_only:
                self._locked_provider = "ollama"
        else:
            raise RuntimeError("No LLM providers available")

        self._initialized = True
        logger.info(
            "LLM router initialized: active=%s, available=%s",
            self.active_provider.get("name") if self.active_provider else None,
            self.available_providers,
        )

    async def _probe_provider(self, name: str) -> dict[str, Any] | None:
        if name == "ollama":
            return await self.settings._probe_ollama()
        for cfg in self.settings.provider_configs():
            if cfg["name"] == name:
                return await self.settings._probe_litellm_provider(cfg)
        return None

    async def _rotate_provider(self) -> bool:
        if self._locked_provider or self.settings.ollama_only:
            return False
        if not self.active_provider:
            return False
        current = self.active_provider.get("name", "")
        order = self._provider_order()
        try:
            idx = order.index(current)
        except ValueError:
            idx = -1

        for name in order[idx + 1 :]:
            cfg = await self._probe_provider(name)
            if cfg:
                self.active_provider = cfg
                if name not in self.available_providers:
                    self.available_providers.append(name)
                logger.warning("Rotated LLM provider to %s", name)
                return True
        return False

    def _build_kwargs(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.active_provider:
            raise RuntimeError("LLM router not initialized")

        kwargs: dict[str, Any] = {
            "model": self.active_provider["model"],
            "messages": messages,
        }

        if self.active_provider.get("api_base"):
            kwargs["api_base"] = self.active_provider["api_base"]
        if self.active_provider.get("api_key"):
            kwargs["api_key"] = self.active_provider["api_key"]

        if self.active_provider.get("name") == "ollama":
            kwargs["timeout"] = self.settings.ollama_timeout_seconds
            kwargs["num_retries"] = 1

        if schema:
            kwargs["response_format"] = {"type": "json_object"}
            kwargs["max_tokens"] = 4096

        return kwargs

    @staticmethod
    def _extract_json(text: str) -> Any:
        text = text.strip()
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence_match:
            text = fence_match.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            array_match = re.search(r"\[[\s\S]*\]", text)
            if array_match:
                return json.loads(array_match.group())
            obj_match = re.search(r"\{[\s\S]*\}", text)
            if obj_match:
                return json.loads(obj_match.group())
            raise

    async def complete(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None = None,
    ) -> str:
        if not self._initialized:
            await self.initialize()

        max_attempts = len(self.available_providers) or 1
        last_error: Exception | None = None

        for _ in range(max_attempts):
            try:
                kwargs = self._build_kwargs(messages, schema)
                start = time.perf_counter()
                response = await litellm.acompletion(**kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                self.last_latency_ms = elapsed

                content = response.choices[0].message.content or ""
                provider_name = self.active_provider.get("name", "unknown")
                model = self.active_provider.get("model", "unknown")
                logger.info(
                    "LLM call: provider=%s model=%s latency=%.0fms tokens=%s",
                    provider_name,
                    model,
                    elapsed,
                    getattr(response.usage, "total_tokens", "?"),
                )
                return content
            except Exception as exc:
                last_error = exc
                logger.error(
                    "LLM call failed (provider=%s): %s",
                    self.active_provider.get("name") if self.active_provider else "?",
                    exc,
                )
                rotated = await self._rotate_provider()
                if not rotated:
                    break

        raise RuntimeError(f"All LLM providers failed: {last_error}")

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None = None,
    ) -> Any:
        content = await self.complete(messages, schema=schema or {})
        try:
            return self._extract_json(content)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to parse LLM JSON response: %s", exc)
            return None

    async def get_status(self) -> dict[str, Any]:
        if not self._initialized:
            try:
                await self.initialize()
            except RuntimeError:
                ollama = await self.settings._probe_ollama()
                if ollama:
                    return {
                        "provider": "ollama",
                        "model": ollama["model"],
                        "latency_ms": None,
                        "available_providers": ["ollama"],
                    }
                return {
                    "provider": "none",
                    "model": "none",
                    "latency_ms": None,
                    "available_providers": [],
                }

        return {
            "provider": self.active_provider.get("name", "unknown")
            if self.active_provider
            else "none",
            "model": self.active_provider.get("model", "unknown")
            if self.active_provider
            else "none",
            "latency_ms": self.last_latency_ms,
            "available_providers": self.available_providers,
        }

    async def health_ping(self) -> float | None:
        try:
            await self.complete(
                [{"role": "user", "content": "Reply with OK"}],
            )
            return self.last_latency_ms
        except Exception:
            return None


_router_instance: LLMRouter | None = None


async def get_llm_router(force_provider: str | None = None) -> LLMRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
        await _router_instance.initialize(force_provider=force_provider)
    elif force_provider and force_provider != "auto":
        await _router_instance.initialize(force_provider=force_provider)
    return _router_instance
