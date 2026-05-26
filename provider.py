"""Hermes WebSearchProvider backed by @thinkscape/smart-fetch CLI.

Implements the :class:`agent.web_search_provider.WebSearchProvider` ABC so
Hermes can route ``web_extract`` calls through smart-fetch's TLS-fingerprinted
fetch + Defuddle extraction pipeline.

Configure in ``~/.hermes/config.yaml``::

    web:
      extract_backend: smartfetch
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from agent.web_search_provider import WebSearchProvider

logger = logging.getLogger(__name__)


class SmartFetchWebSearchProvider(WebSearchProvider):
    """Web extract provider using @thinkscape/smart-fetch CLI.

    Extract-only (no search) — pair with ``ddgs``, ``brave-free``, or any
    other search backend for ``web_search``.
    """

    @property
    def name(self) -> str:
        return "smartfetch"

    @property
    def display_name(self) -> str:
        return "Smart Fetch (local)"

    def is_available(self) -> bool:
        """Return True when the smart-fetch CLI is reachable.

        Checks for global install first (smart-fetch / sf), then npx fallback.
        No API key required — runs entirely locally.
        """
        import shutil
        if shutil.which("smart-fetch") or shutil.which("sf"):
            return True
        # npx fallback — check if npx itself is available
        if shutil.which("npx"):
            return True
        return False

    def supports_search(self) -> bool:
        return False

    def supports_extract(self) -> bool:
        return True

    def supports_crawl(self) -> bool:
        return False

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        raise NotImplementedError(
            "smartfetch is an extract-only provider. Use ddgs for search."
        )

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        """Extract content from one or more URLs via smart-fetch.

        Returns the standard Hermes ``web_extract`` result shape::

            [
                {
                    "url": str,
                    "title": str,
                    "content": str,
                    "raw_content": str,
                    "metadata": dict,
                    "error": str,  # only on failure
                },
                ...
            ]
        """
        from smart_fetch_client import smart_fetch

        if not urls:
            return []

        # Read defaults from environment (user can override via env vars)
        browser = os.environ.get("SMART_FETCH_BROWSER", "chrome_145")
        os_profile = os.environ.get("SMART_FETCH_OS", "macos")
        max_chars = int(os.environ.get("SMART_FETCH_MAX_CHARS", "50000"))
        timeout_ms = int(os.environ.get("SMART_FETCH_TIMEOUT_MS", "15000"))

        # Call smart-fetch
        batch = smart_fetch(
            urls,
            browser=browser,
            os_profile=os_profile,
            format="markdown",
            max_chars=max_chars,
            timeout_ms=timeout_ms,
            verbose=True,
        )

        # Convert to Hermes response shape
        results: List[Dict[str, Any]] = []

        for item in batch.items:
            if item.error:
                results.append({
                    "url": item.url,
                    "title": "",
                    "content": "",
                    "raw_content": "",
                    "error": item.error,
                    "metadata": {"sourceURL": item.url},
                })
            else:
                results.append({
                    "url": item.url,
                    "title": item.title or "",
                    "content": item.content,
                    "raw_content": item.content,
                    "metadata": {
                        "sourceURL": item.final_url or item.url,
                        "title": item.title or "",
                        "author": item.author or "",
                        "published": item.published or "",
                        "language": item.language or "",
                        "word_count": item.word_count,
                    },
                })

        return results

    def get_setup_schema(self) -> Dict[str, Any]:
        """Return provider metadata for the ``hermes tools`` picker."""
        return {
            "name": "Smart Fetch (local)",
            "badge": "free",
            "tag": "Local, no API key — TLS fingerprinting + Defuddle extraction.",
            "env_vars": [],
        }
