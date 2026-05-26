"""hermes-smart-fetch — Hermes Agent plugin for @thinkscape/smart-fetch.

Provides browser-grade TLS fingerprinting + Defuddle content extraction
as a local, API-key-free web backend for Hermes Agent.

Registration:
  • WebSearchProvider → use ``web.extract_backend: smartfetch`` in config
  • web_fetch tool    → single URL fetch with full parameter control
  • batch_web_fetch   → batch fetch with bounded concurrency

Install:
  hermes plugins install /path/to/hermes-smart-fetch --enable

Or symlink into ~/.hermes/plugins/:
  ln -s /path/to/hermes-smart-fetch ~/.hermes/plugins/hermes-smart-fetch

Requires:
  • Node.js 18+ (for @thinkscape/smart-fetch CLI)
  • npm install -g @thinkscape/smart-fetch  (or npx fallback)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Add plugin directory to sys.path so sibling modules are importable
_plugin_dir = str(Path(__file__).parent)
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)


def register(context) -> None:
    """Hermes plugin entry point.

    Called by the Hermes plugin loader during startup. Registers:
      1. A WebSearchProvider for web_extract backend routing
      2. Standalone web_fetch and batch_web_fetch tools
    """
    # -- 1. Register the WebSearchProvider -----------------------------------
    try:
        from provider import SmartFetchWebSearchProvider

        provider = SmartFetchWebSearchProvider()
        context.register_web_search_provider(provider)
        logger.info(
            "hermes-smart-fetch: registered web provider '%s' "
            "(extract_backend available)",
            provider.name,
        )
    except Exception as exc:
        logger.warning("hermes-smart-fetch: failed to register web provider: %s", exc)

    # -- 2. Register standalone tools ----------------------------------------
    try:
        from tools import register_tools

        # The context object exposes the tool registry
        register_tools(context.tool_registry)
        logger.info("hermes-smart-fetch: registered web_fetch + batch_web_fetch tools")
    except Exception as exc:
        logger.warning("hermes-smart-fetch: failed to register tools: %s", exc)

    # -- 3. CLI availability check -------------------------------------------
    try:
        from smart_fetch_client import check_availability

        if check_availability():
            logger.info("hermes-smart-fetch: smart-fetch CLI detected ✓")
        else:
            logger.warning(
                "hermes-smart-fetch: smart-fetch CLI not found. "
                "Install with: npm install -g @thinkscape/smart-fetch"
            )
    except Exception:
        pass
