"""Standalone Hermes tools: web_fetch and batch_web_fetch.

Registers two model-callable tools with the same parameter surface as
pi-smart-fetch / openclaw-smart-fetch:

  • web_fetch       — single URL fetch with TLS fingerprinting
  • batch_web_fetch — batch fetch with bounded concurrency

These are registered alongside the WebSearchProvider (provider.py) so the
agent can call them directly for full control over browser profile, OS
fingerprint, output format, etc.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

# Parameter descriptions (matching pi-smart-fetch surface)
_PARAM_URL_DESC = "The URL to fetch. Must be a valid http:// or https:// URL."
_PARAM_BROWSER_DESC = (
    "Browser profile for TLS fingerprinting. "
    "Options: chrome_145 (default), firefox_147, safari_26, edge_145, opera_127."
)
_PARAM_OS_DESC = (
    "OS profile for fingerprinting. "
    "Options: macos (default), windows, linux, android, ios."
)
_PARAM_FORMAT_DESC = (
    "Output format. Options: markdown (default), html, text, raw."
)
_PARAM_MAX_CHARS_DESC = (
    "Maximum characters to return. Default: 50000."
)
_PARAM_TIMEOUT_DESC = (
    "Request timeout in milliseconds. Default: 15000."
)
_PARAM_REMOVE_IMAGES_DESC = (
    "Strip image references from output. Default: false."
)
_PARAM_INCLUDE_REPLIES_DESC = (
    "Include replies/comments. Options: extractors (default), true, false."
)
_PARAM_PROXY_DESC = (
    "Proxy URL (http://user:pass@host:port or socks5://...). Optional."
)
_PARAM_VERBOSE_DESC = (
    "Include full metadata header (title, language, word count, etc). Default: true."
)


def _check_requirements() -> bool:
    """Return True if smart-fetch CLI is reachable."""
    import shutil
    if shutil.which("smart-fetch") or shutil.which("sf"):
        return True
    if shutil.which("npx"):
        return True
    return False


def _web_fetch_handler(args: Dict[str, Any], **kwargs: Any) -> str:
    """Handler for the web_fetch tool."""
    from smart_fetch_client import smart_fetch_single

    url = args.get("url", "")
    if not url:
        return json.dumps({"success": False, "error": "url is required"})

    result = smart_fetch_single(
        url,
        browser=args.get("browser", "chrome_145"),
        os_profile=args.get("os", "macos"),
        format=args.get("format", "markdown"),
        max_chars=args.get("maxChars", 50000),
        timeout_ms=args.get("timeoutMs", 15000),
        remove_images=args.get("removeImages", False),
        include_replies=args.get("includeReplies", "extractors"),
        proxy=args.get("proxy"),
        verbose=args.get("verbose", True),
    )

    if result.error:
        return json.dumps({
            "success": False,
            "url": url,
            "error": result.error,
        })

    return json.dumps({
        "success": True,
        "url": result.url,
        "final_url": result.final_url,
        "title": result.title,
        "author": result.author,
        "published": result.published,
        "language": result.language,
        "site": result.site,
        "word_count": result.word_count,
        "browser": result.browser,
        "content_type": result.content_type,
        "content": result.content,
    })


def _batch_web_fetch_handler(args: Dict[str, Any], **kwargs: Any) -> str:
    """Handler for the batch_web_fetch tool."""
    from smart_fetch_client import smart_fetch

    urls = args.get("urls", [])
    if not urls:
        return json.dumps({"success": False, "error": "urls list is required"})

    result = smart_fetch(
        urls,
        browser=args.get("browser", "chrome_145"),
        os_profile=args.get("os", "macos"),
        format=args.get("format", "markdown"),
        max_chars=args.get("maxChars", 50000),
        timeout_ms=args.get("timeoutMs", 15000),
        remove_images=args.get("removeImages", False),
        include_replies=args.get("includeReplies", "extractors"),
        proxy=args.get("proxy"),
        concurrency=args.get("concurrency", 8),
        verbose=args.get("verbose", True),
    )

    items = []
    for item in result.items:
        if item.error:
            items.append({
                "url": item.url,
                "error": item.error,
            })
        else:
            items.append({
                "url": item.url,
                "final_url": item.final_url,
                "title": item.title,
                "author": item.author,
                "published": item.published,
                "language": item.language,
                "word_count": item.word_count,
                "content": item.content,
            })

    return json.dumps({
        "success": True,
        "total": len(urls),
        "succeeded": result.succeeded,
        "failed": result.failed,
        "items": items,
    })


def register_tools(registry: Any) -> None:
    """Register web_fetch and batch_web_fetch in the Hermes tool registry.

    Called from ``__init__.py`` during plugin registration.
    """

    # -- web_fetch -----------------------------------------------------------
    registry.register(
        name="web_fetch",
        toolset="web",
        schema={
            "name": "web_fetch",
            "description": (
                "Fetch a URL with browser-grade TLS fingerprinting and extract "
                "clean, readable content. Uses wreq-js for browser-like "
                "TLS/HTTP2 impersonation and Defuddle for article extraction. "
                "Returns full metadata plus the extracted document. "
                "Does NOT execute JavaScript — use a browser tool for JS-heavy pages."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": _PARAM_URL_DESC,
                    },
                    "browser": {
                        "type": "string",
                        "description": _PARAM_BROWSER_DESC,
                        "default": "chrome_145",
                    },
                    "os": {
                        "type": "string",
                        "description": _PARAM_OS_DESC,
                        "default": "macos",
                    },
                    "format": {
                        "type": "string",
                        "description": _PARAM_FORMAT_DESC,
                        "default": "markdown",
                    },
                    "maxChars": {
                        "type": "integer",
                        "description": _PARAM_MAX_CHARS_DESC,
                        "default": 50000,
                    },
                    "timeoutMs": {
                        "type": "integer",
                        "description": _PARAM_TIMEOUT_DESC,
                        "default": 15000,
                    },
                    "removeImages": {
                        "type": "boolean",
                        "description": _PARAM_REMOVE_IMAGES_DESC,
                        "default": False,
                    },
                    "includeReplies": {
                        "type": "string",
                        "description": _PARAM_INCLUDE_REPLIES_DESC,
                        "default": "extractors",
                    },
                    "proxy": {
                        "type": "string",
                        "description": _PARAM_PROXY_DESC,
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": _PARAM_VERBOSE_DESC,
                        "default": True,
                    },
                },
                "required": ["url"],
            },
        },
        handler=lambda args, **kw: _web_fetch_handler(args, **kw),
        check_fn=_check_requirements,
    )

    # -- batch_web_fetch -----------------------------------------------------
    registry.register(
        name="batch_web_fetch",
        toolset="web",
        schema={
            "name": "batch_web_fetch",
            "description": (
                "Fetch multiple URLs with browser-grade TLS fingerprinting and "
                "readable extraction. Each URL runs with bounded concurrency. "
                "Returns clearly labeled per-item results with full content for "
                "successes and per-item errors for failures. "
                "Does NOT execute JavaScript — use a browser tool for JS-heavy pages."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of URLs to fetch.",
                    },
                    "browser": {
                        "type": "string",
                        "description": _PARAM_BROWSER_DESC,
                        "default": "chrome_145",
                    },
                    "os": {
                        "type": "string",
                        "description": _PARAM_OS_DESC,
                        "default": "macos",
                    },
                    "format": {
                        "type": "string",
                        "description": _PARAM_FORMAT_DESC,
                        "default": "markdown",
                    },
                    "maxChars": {
                        "type": "integer",
                        "description": _PARAM_MAX_CHARS_DESC,
                        "default": 50000,
                    },
                    "timeoutMs": {
                        "type": "integer",
                        "description": _PARAM_TIMEOUT_DESC,
                        "default": 15000,
                    },
                    "removeImages": {
                        "type": "boolean",
                        "description": _PARAM_REMOVE_IMAGES_DESC,
                        "default": False,
                    },
                    "includeReplies": {
                        "type": "string",
                        "description": _PARAM_INCLUDE_REPLIES_DESC,
                        "default": "extractors",
                    },
                    "proxy": {
                        "type": "string",
                        "description": _PARAM_PROXY_DESC,
                    },
                    "concurrency": {
                        "type": "integer",
                        "description": "Max concurrent requests. Default: 8.",
                        "default": 8,
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": _PARAM_VERBOSE_DESC,
                        "default": True,
                    },
                },
                "required": ["urls"],
            },
        },
        handler=lambda args, **kw: _batch_web_fetch_handler(args, **kw),
        check_fn=_check_requirements,
    )
