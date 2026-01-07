"""
LLM Client - Generic OpenAI-compatible HTTP client

Supports any OpenAI-compatible API (local LLM, OpenAI, Anthropic, etc.)
Configurable via environment variables.
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Generic LLM client for OpenAI-compatible APIs.
    
    Configurable via environment variables:
    - ORCHESTRATOR_LLM_URL: API endpoint (default: http://localhost:8001/v1/chat/completions)
    - ORCHESTRATOR_LLM_API_KEY: API key (optional, default: token-irrelevant)
    - ORCHESTRATOR_LLM_MODEL: Model name (optional, default: mistralai/Mistral-7B-Instruct-v0.3)
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize LLM client.
        
        Args:
            api_url: LLM API endpoint. If not provided, uses ORCHESTRATOR_LLM_URL env var.
            api_key: API key for authentication. If not provided, uses ORCHESTRATOR_LLM_API_KEY env var.
            model: Model name. If not provided, uses ORCHESTRATOR_LLM_MODEL env var.
        """
        self.api_url = api_url or os.getenv(
            "ORCHESTRATOR_LLM_URL", "http://localhost:8001/v1/chat/completions"
        )
        self.api_key = api_key or os.getenv("ORCHESTRATOR_LLM_API_KEY", "token-irrelevant")
        self.model = model or os.getenv(
            "ORCHESTRATOR_LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.3"
        )
        self.client = httpx.AsyncClient(timeout=600.0)  # 10 minutes for comprehensive discovery (matches API gateway)

    async def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        """
        Send chat completion request to LLM.
        
        Args:
            system_prompt: System message/prompt
            user_message: User message
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Returns:
            LLM response content
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        logger.debug(f"Sending request to LLM: {self.api_url}")
        logger.debug(f"System prompt length: {len(system_prompt)} characters")
        logger.debug(f"User message: {user_message[:100]}...")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await self.client.post(self.api_url, json=payload, headers=headers)
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"LLM API request failed: {response.status_code} - {error_text[:500]}")
                try:
                    error_json = response.json()
                    logger.error(f"Error details: {error_json}")
                except:
                    pass
                response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            usage = data.get("usage", {})
            logger.debug(
                f"LLM response: {usage.get('prompt_tokens', '?')} prompt tokens, "
                f"{usage.get('completion_tokens', '?')} completion tokens"
            )
            
            return content
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API request failed: {e}")
            if e.response:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text[:500]}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"LLM API request failed: {e}")
            raise
        except KeyError as e:
            logger.error(f"Unexpected LLM response format: {e}")
            raise ValueError(f"Invalid LLM response format: {e}") from e

    async def health_check(self) -> bool:
        """
        Check if LLM service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Try to hit health endpoint if it exists
            health_url = self.api_url.replace("/v1/chat/completions", "/health")
            response = await self.client.get(health_url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "healthy"
            return False
        except Exception:
            # If health check fails, try a minimal chat completion
            try:
                await self.chat_completion(
                    system_prompt="You are a helpful assistant.",
                    user_message="Health check",
                    max_tokens=10,
                )
                return True
            except Exception:
                return False

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

