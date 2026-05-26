"""Smart Fetch CLI client — bridges Python to the @thinkscape/smart-fetch binary.

Handles:
  • Locating the smart-fetch / sf binary (global install, npx fallback)
  • Calling it with the right flags
  • Parsing verbose output into structured results
  • Error handling and timeouts
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class FetchResult:
    """Structured result from a single smart-fetch call."""

    url: str = ""
    final_url: str = ""
    title: str = ""
    language: str = ""
    author: str = ""
    published: str = ""
    site: str = ""
    word_count: int = 0
    browser: str = ""
    content: str = ""
    content_type: str = ""
    raw_output: str = ""
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.content.strip())


@dataclass
class BatchFetchResult:
    """Structured result from a batch smart-fetch call."""

    items: List[FetchResult] = field(default_factory=list)
    raw_output: str = ""

    @property
    def succeeded(self) -> int:
        return sum(1 for i in self.items if i.ok)

    @property
    def failed(self) -> int:
        return sum(1 for i in self.items if not i.ok)


# ---------------------------------------------------------------------------
# CLI configuration
# ---------------------------------------------------------------------------

# Defaults matching @thinkscape/smart-fetch CLI
DEFAULT_BROWSER = "chrome_145"
DEFAULT_OS = "macos"
DEFAULT_FORMAT = "markdown"
DEFAULT_MAX_CHARS = 50_000
DEFAULT_TIMEOUT_MS = 15_000
DEFAULT_CONCURRENCY = 8
DEFAULT_REMOVE_IMAGES = False


def _find_smart_fetch_binary() -> Optional[str]:
    """Locate the smart-fetch or sf binary on PATH."""
    for name in ("smart-fetch", "sf"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _smart_fetch_command() -> List[str]:
    """Return the base command to invoke smart-fetch.

    Tries global install first, falls back to npx.
    """
    binary = _find_smart_fetch_binary()
    if binary:
        return [binary]
    # npx fallback — works even without global install
    return ["npx", "@thinkscape/smart-fetch"]


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

# Verbose header lines look like:
#   > URL: https://example.com/
#   > Title: Example Domain
#   > Language: en
#   > Author: John Doe
#   > Published: 2025-01-15
#   > Site: example.com
#   > Words: 42
#   > Browser: chrome_145/windows
#   > Content-Type: text/html
_HEADER_RE = re.compile(r"^>\s*(URL|Title|Language|Author|Published|Site|Words|Browser|Content-Type):\s*(.*)$")


def _parse_verbose_output(output: str) -> FetchResult:
    """Parse smart-fetch --verbose output into a FetchResult."""
    result = FetchResult(raw_output=output)
    lines = output.split("\n")
    content_start = 0

    for i, line in enumerate(lines):
        m = _HEADER_RE.match(line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            if key == "URL":
                result.url = value
                result.final_url = value
            elif key == "Title":
                result.title = value
            elif key == "Language":
                result.language = value
            elif key == "Author":
                result.author = value
            elif key == "Published":
                result.published = value
            elif key == "Site":
                result.site = value
            elif key == "Words":
                try:
                    result.word_count = int(value)
                except ValueError:
                    pass
            elif key == "Browser":
                result.browser = value
            elif key == "Content-Type":
                result.content_type = value
            content_start = i + 1
        elif line.startswith("> "):
            # Unknown header line — skip
            content_start = i + 1
        else:
            # First non-header line — content starts here
            break

    # Content is everything after the header block
    content_lines = lines[content_start:]
    # Strip leading/trailing blank lines
    while content_lines and not content_lines[0].strip():
        content_lines.pop(0)
    while content_lines and not content_lines[-1].strip():
        content_lines.pop()
    result.content = "\n".join(content_lines)

    return result


def _parse_error_output(output: str, exit_code: int) -> str:
    """Extract a meaningful error message from failed output."""
    # Try to find error-like lines
    for line in output.split("\n"):
        line = line.strip()
        if line.lower().startswith("error") or line.lower().startswith("fatal"):
            return line
    if output.strip():
        return output.strip().split("\n")[0][:200]
    return f"smart-fetch exited with code {exit_code}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def smart_fetch(
    urls: List[str],
    *,
    browser: str = DEFAULT_BROWSER,
    os_profile: str = DEFAULT_OS,
    format: str = DEFAULT_FORMAT,
    max_chars: int = DEFAULT_MAX_CHARS,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    remove_images: bool = DEFAULT_REMOVE_IMAGES,
    include_replies: str = "extractors",
    proxy: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    concurrency: int = DEFAULT_CONCURRENCY,
    verbose: bool = True,
) -> BatchFetchResult:
    """Fetch one or more URLs via the smart-fetch CLI.

    Returns a BatchFetchResult with one FetchResult per URL.
    """
    if not urls:
        return BatchFetchResult()

    cmd = _smart_fetch_command()

    # Build command arguments
    args: List[str] = []

    # Options
    args.extend(["--browser", browser])
    args.extend(["--os", os_profile])
    args.extend(["--format", format])
    args.extend(["--max-chars", str(max_chars)])
    args.extend(["--timeout", str(timeout_ms)])
    args.extend(["--concurrency", str(concurrency)])

    if include_replies:
        args.extend(["--include-replies", include_replies])

    if remove_images:
        args.append("--remove-images")

    if proxy:
        args.extend(["--proxy", proxy])

    if verbose:
        args.append("--verbose")

    # Suppress progress output for cleaner parsing
    args.append("--no-progress")

    # URLs last
    args.extend(urls)

    full_cmd = cmd + args
    logger.info("smart-fetch: %s", " ".join(full_cmd[:6]) + " ...")

    try:
        # Build env with PATH augmented for npx
        env = os.environ.copy()
        node_bin = str(Path.home() / ".nvm" / "versions" / "node" / "v23.5.0" / "bin")
        if node_bin not in env.get("PATH", ""):
            env["PATH"] = node_bin + ":" + env.get("PATH", "")

        proc = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=max(30, (timeout_ms // 1000) * len(urls) + 30),
            env=env,
        )

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        if proc.returncode != 0 and not stdout:
            error_msg = _parse_error_output(stderr or stdout, proc.returncode)
            return BatchFetchResult(
                items=[FetchResult(url=u, error=error_msg, raw_output=stderr) for u in urls],
                raw_output=stderr,
            )

        # For single URL, parse directly
        if len(urls) == 1:
            result = _parse_verbose_output(stdout)
            if not result.url:
                result.url = urls[0]
            if proc.returncode != 0 and not result.content:
                result.error = _parse_error_output(stderr or stdout, proc.returncode)
            return BatchFetchResult(items=[result], raw_output=stdout)

        # For batch, split output by URL markers
        results = _split_batch_output(stdout, urls)
        return BatchFetchResult(items=results, raw_output=stdout)

    except subprocess.TimeoutExpired:
        logger.warning("smart-fetch timed out for %d URL(s)", len(urls))
        return BatchFetchResult(
            items=[FetchResult(url=u, error="Request timed out") for u in urls],
        )
    except FileNotFoundError:
        msg = (
            "smart-fetch CLI not found. Install with: "
            "npm install -g @thinkscape/smart-fetch"
        )
        logger.error(msg)
        return BatchFetchResult(
            items=[FetchResult(url=u, error=msg) for u in urls],
        )
    except Exception as exc:
        logger.error("smart-fetch unexpected error: %s", exc)
        return BatchFetchResult(
            items=[FetchResult(url=u, error=str(exc)) for u in urls],
        )


def _split_batch_output(output: str, urls: List[str]) -> List[FetchResult]:
    """Split batch output into per-URL results.

    Each result block starts with '> URL: ...' when verbose mode is on.
    """
    # Split on the URL header pattern
    blocks = re.split(r"(?=^> URL: )", output, flags=re.MULTILINE)
    blocks = [b for b in blocks if b.strip()]

    results: List[FetchResult] = []

    for block in blocks:
        result = _parse_verbose_output(block)
        if result.url:
            results.append(result)

    # If we didn't get enough results, fill with errors for missing URLs
    found_urls = {r.url.rstrip("/") for r in results}
    for url in urls:
        normalized = url.rstrip("/")
        if normalized not in found_urls:
            results.append(FetchResult(url=url, error="No output produced for this URL"))

    return results


def smart_fetch_single(
    url: str,
    **kwargs: Any,
) -> FetchResult:
    """Convenience wrapper for a single URL fetch."""
    result = smart_fetch([url], **kwargs)
    if result.items:
        return result.items[0]
    return FetchResult(url=url, error="No result produced")


def check_availability() -> bool:
    """Check if smart-fetch CLI is available."""
    try:
        binary = _find_smart_fetch_binary()
        if binary:
            return True
        # Try npx
        proc = subprocess.run(
            ["npx", "@thinkscape/smart-fetch", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return proc.returncode == 0
    except Exception:
        return False
