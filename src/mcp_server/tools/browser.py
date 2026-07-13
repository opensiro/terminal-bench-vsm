"""browser tools — fetch/search (optional, for web-tasks)."""
from __future__ import annotations
import json
import urllib.request
import urllib.parse
import time


def register_browser_tools(server):
    def browser_fetch(url: str) -> dict:
        start = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "coding-harness/0.1"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="replace")
                return {"stdout": content[:50000], "stderr": "", "exit_code": 0, "time_seconds": time.time() - start}
        except Exception as exc:
            return {"stdout": "", "stderr": str(exc), "exit_code": 1, "time_seconds": time.time() - start}

    def browser_search(query: str) -> dict:
        # Minimal: uses DuckDuckGo HTML (no API key needed).
        start = time.time()
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={"User-Agent": "coding-harness/0.1"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="replace")
                return {"stdout": content[:50000], "stderr": "", "exit_code": 0, "time_seconds": time.time() - start}
        except Exception as exc:
            return {"stdout": "", "stderr": str(exc), "exit_code": 1, "time_seconds": time.time() - start}

    server.register("browser.fetch", "HTTP GET", {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}, browser_fetch)
    server.register("browser.search", "web search", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, browser_search)
