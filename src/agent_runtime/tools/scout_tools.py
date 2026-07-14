"""scout_tools — S4 intelligence tools: intel.json read/write (VSM-016).

S4 scout writes discovered signals to state/intel.json (the product's
intelligence store). These tools give the goose-agent structured access.

Tools:
  intel_write(signals)  → append signals to state/intel.json (atomic)
  intel_read()          → read current signals + coverage
  taxonomy_read()       → reuse S3 classifier tool (check coverage gaps)

Membrane (VSM-002): intel.json is product state (coding patterns, recovery
techniques) — benchmark-agnostic by construction. The agent is instructed
(SOUL) to keep scope general-purpose.
"""
from __future__ import annotations

import json
import time
from pathlib import Path


def register_scout_tools(server, workspace: str):
    """Register S4 intelligence tools onto the MCP server.

    Args:
        server: MCPServer to register tools onto.
        workspace: vsm/ root (where state/intel.json lives).
    """
    # state/intel.json lives in <workspace>/state/intel.json (workspace = vsm/)
    intel_path = Path(workspace) / "state" / "intel.json"

    def _load_intel() -> dict:
        """Load intel.json (or empty skeleton if missing/corrupt)."""
        if not intel_path.exists():
            return {
                "_comment": "intel.json — S4 signals. Пишет s4-scout.",
                "generated": time.strftime("%Y-%m-%d"),
                "scanner": "s4-scout",
                "signals": [],
                "coverage": {},
            }
        try:
            data = json.loads(intel_path.read_text(encoding="utf-8"))
            if "signals" not in data:
                data["signals"] = []
            return data
        except (json.JSONDecodeError, OSError):
            return {"signals": [], "coverage": {}}

    def _save_intel(data: dict) -> None:
        """Atomically save intel.json (temp → rename)."""
        intel_path.parent.mkdir(parents=True, exist_ok=True)
        data["generated"] = time.strftime("%Y-%m-%d")
        data["scanner"] = "s4-scout"
        payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        import tempfile, os
        fd, tmp = tempfile.mkstemp(dir=str(intel_path.parent), suffix=".tmp")
        try:
            os.write(fd, payload.encode("utf-8"))
            os.close(fd)
            os.replace(tmp, intel_path)
        except Exception:
            os.close(fd)
            Path(tmp).unlink(missing_ok=True)
            raise

    def intel_write(signals: list) -> dict:
        """Append discovered signals to state/intel.json.

        Each signal: {type, severity, summary, detail, status}.
        """
        try:
            if not isinstance(signals, list):
                return {"error": "signals must be a list", "exit_code": 1}
            data = _load_intel()
            ts = time.strftime("%Y-%m-%dT%H:%M:%S")
            for sig in signals:
                if isinstance(sig, dict):
                    sig.setdefault("status", "triage")
                    sig.setdefault("added", ts)
                    data["signals"].append(sig)
            _save_intel(data)
            return {"written": len(signals), "total_signals": len(data["signals"]),
                    "exit_code": 0}
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "exit_code": 1}

    server.register(
        "intel_write",
        "append discovered signals to state/intel.json (S4 intelligence store)",
        {
            "type": "object",
            "properties": {
                "signals": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "signals to append: {type, severity, summary, detail, status}",
                },
            },
            "required": ["signals"],
        },
        intel_write,
    )

    def intel_read() -> dict:
        """Read current signals + coverage from state/intel.json."""
        try:
            data = _load_intel()
            return {
                "signals": data.get("signals", []),
                "coverage": data.get("coverage", {}),
                "total": len(data.get("signals", [])),
                "exit_code": 0,
            }
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "exit_code": 1}

    server.register(
        "intel_read",
        "read current signals and coverage from state/intel.json",
        {"type": "object", "properties": {}, "required": []},
        intel_read,
    )
