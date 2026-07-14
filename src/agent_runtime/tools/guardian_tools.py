"""guardian_tools — S5 architect tools: identity read, OSM primitives, issue resolve (VSM-017).

S5 guardian is the autonomous architect (VSM-006). These tools let the goose-agent:
  - identity_read: read vsm.yaml identity/values/never_do (to guard invariants)
  - osm_apply: apply a structural OSM primitive (Split/Merge/Reconfigure) — logs
    the intervention (observable by parent VSM-005 metric). Does NOT mutate
    identity/values/never_do (the single autonomy limit).
  - issue_resolve: record a decision on a VSM-NNN issue (status, decision text)
  - algedonic_log: log an S5 intervention (structural change on algedonic)

Membrane (VSM-002): S5 operates on product structure (vsm/), benchmark-agnostic.
Identity change is blocked — requires parent VSM-NNN (the only autonomy exception).
"""
from __future__ import annotations

import json
import time
from pathlib import Path


def register_guardian_tools(server, workspace: str):
    """Register S5 architect tools onto the MCP server.

    Args:
        server: MCPServer to register tools onto.
        workspace: vsm/ root (where vsm.yaml, issues/, state/ live).
    """
    vsm_yaml_path = Path(workspace) / "vsm.yaml"
    issues_dir = Path(workspace) / "issues"
    interventions_path = Path(workspace) / "state" / "interventions.json"

    def identity_read() -> dict:
        """Read identity/values/never_do from vsm.yaml (read-only).

        S5 uses this to guard invariants: never_do violations, identity drift.
        Returns the identity section + never_do list.
        """
        try:
            import yaml
            if not vsm_yaml_path.exists():
                return {"error": "vsm.yaml not found", "exit_code": 1}
            data = yaml.safe_load(vsm_yaml_path.read_text(encoding="utf-8"))
            identity = data.get("identity", {}) if isinstance(data, dict) else {}
            return {
                "purpose": identity.get("purpose", ""),
                "values": identity.get("values", []),
                "never_do": identity.get("never_do", []),
                "exit_code": 0,
            }
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "exit_code": 1}

    server.register(
        "identity_read",
        "read identity/values/never_do from vsm.yaml (S5 invariant guard)",
        {"type": "object", "properties": {}, "required": []},
        identity_read,
    )

    def osm_apply(primitive: str, target: str = "", rationale: str = "") -> dict:
        """Apply an OSM structural primitive (Split/Merge/Reconfigure).

        Records the intervention (observable by parent VSM-005 metric). This is
        a DECLARATIVE log — the actual structural mutation is performed by the
        product's own s1-dispatcher (membrane: agent declares, dispatcher executes).
        S5 does NOT directly mutate vsm/ files here.

        Args:
            primitive: "Split" | "Merge" | "Reconfigure" | "Intersection" | "Remove"
            target: target unit/path (e.g. "s1-dispatcher", "system_3")
            rationale: why this primitive is needed
        """
        allowed = {"Split", "Merge", "Reconfigure", "Intersection", "Remove"}
        if primitive not in allowed:
            return {"error": f"unknown primitive: {primitive} (allowed: {allowed})",
                    "exit_code": 1}
        intervention = {
            "primitive": primitive,
            "target": target,
            "rationale": rationale,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "declared_by": "s5-guardian",
        }
        # Log intervention (observable by parent VSM-005 intervention metric)
        _append_intervention(interventions_path, intervention)
        return {
            "declared": True,
            "primitive": primitive,
            "target": target,
            "note": "declarative — s1-dispatcher executes the structural change",
            "exit_code": 0,
        }

    server.register(
        "osm_apply",
        "declare an OSM structural primitive (Split/Merge/Reconfigure); logged as intervention",
        {
            "type": "object",
            "properties": {
                "primitive": {"type": "string"},
                "target": {"type": "string", "default": ""},
                "rationale": {"type": "string", "default": ""},
            },
            "required": ["primitive"],
        },
        osm_apply,
    )

    def issue_resolve(issue_id: str, decision: str, status: str = "done") -> dict:
        """Record a decision on a VSM-NNN issue (autonomous resolution).

        Updates issues/<id>.yaml: sets decision + status. S5 resolves issues
        autonomously (VSM-006) — does NOT escalate to human.

        Args:
            issue_id: e.g. "VSM-NNN" (the issue filename stem)
            decision: decision text
            status: "done" | "blocked" | "wontfix"
        """
        try:
            issue_path = issues_dir / f"{issue_id}.yaml"
            if not issue_path.exists():
                return {"error": f"issue not found: {issue_id}", "exit_code": 1}
            import yaml
            text = issue_path.read_text(encoding="utf-8")
            # Line-based update (avoid full yaml round-trip losing comments)
            lines = text.splitlines()
            updated = {"decision": False, "status": False}
            for i, line in enumerate(lines):
                stripped = line.lstrip()
                if stripped.startswith("decision:") and not updated["decision"]:
                    indent = line[:len(line) - len(stripped)]
                    lines[i] = f'{indent}decision: "{decision}"'
                    updated["decision"] = True
                elif stripped.startswith("status:") and not updated["status"]:
                    indent = line[:len(line) - len(stripped)]
                    lines[i] = f"{indent}status: {status}"
                    updated["status"] = True
            issue_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return {"resolved": issue_id, "status": status, "updated_fields": updated,
                    "exit_code": 0}
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "exit_code": 1}

    server.register(
        "issue_resolve",
        "record a decision on a VSM-NNN issue (autonomous resolution, VSM-006)",
        {
            "type": "object",
            "properties": {
                "issue_id": {"type": "string"},
                "decision": {"type": "string"},
                "status": {"type": "string", "default": "done"},
            },
            "required": ["issue_id", "decision"],
        },
        issue_resolve,
    )

    def algedonic_log(source: str, severity: str, action: str, detail: str = "") -> dict:
        """Log an S5 intervention triggered by an algedonic signal.

        Records to state/interventions.json (observable by parent VSM-005 metric).
        Every S5 structural intervention on algedonic = +1 to intervention count.
        """
        intervention = {
            "source": source,
            "severity": severity,
            "action": action,
            "detail": detail,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "declared_by": "s5-guardian",
            "trigger": "algedonic",
        }
        _append_intervention(interventions_path, intervention)
        return {"logged": True, "exit_code": 0}

    server.register(
        "algedonic_log",
        "log an S5 intervention on an algedonic signal (VSM-005 observable)",
        {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "severity": {"type": "string"},
                "action": {"type": "string"},
                "detail": {"type": "string", "default": ""},
            },
            "required": ["source", "severity", "action"],
        },
        algedonic_log,
    )


def _append_intervention(path: Path, entry: dict) -> None:
    """Append an intervention record to state/interventions.json (atomic)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"_comment": "interventions.json — S5 structural interventions (VSM-005).",
            "interventions": []}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and "interventions" in loaded:
                data = loaded
        except (json.JSONDecodeError, OSError):
            pass
    data.setdefault("interventions", []).append(entry)
    data["generated"] = time.strftime("%Y-%m-%d")
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    import tempfile, os
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        os.write(fd, payload.encode("utf-8"))
        os.close(fd)
        os.replace(tmp, path)
    except Exception:
        os.close(fd)
        Path(tmp).unlink(missing_ok=True)
        raise
