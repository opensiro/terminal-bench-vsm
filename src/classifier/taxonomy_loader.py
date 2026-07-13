"""taxonomy_loader — loads and parses failure_taxonomy.yaml."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .types import TaxonomyClass


def load_taxonomy(taxonomy_path: str | Path) -> dict[str, Any]:
    """Load raw taxonomy YAML. Returns parsed dict."""
    import yaml
    path = Path(taxonomy_path)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_classes(taxonomy: dict[str, Any]) -> list[TaxonomyClass]:
    """Parse failure_classes from taxonomy dict into TaxonomyClass objects."""
    classes = []
    for raw in taxonomy.get("failure_classes", []):
        classes.append(TaxonomyClass(
            id=raw["id"],
            category=raw.get("category", "unknown"),
            description=raw.get("description", ""),
            signals=raw.get("signals") or [],
            recovery_policy=raw.get("recovery_policy", "EscalateToS3"),
            recovery_steps=raw.get("recovery_steps") or [],
            s2_anti_repeat=raw.get("s2_anti_repeat", ""),
        ))
    return classes


def get_match_order(taxonomy: dict[str, Any]) -> list[str]:
    """Get classifier_guidance.match_order from taxonomy."""
    guidance = taxonomy.get("classifier_guidance", {})
    return guidance.get("match_order") or [
        "code", "dependency", "git", "resource", "network", "environment", "spec", "fallback"
    ]


def get_multi_match_resolution(taxonomy: dict[str, Any]) -> str:
    """Get classifier_guidance.multi_match_resolution."""
    guidance = taxonomy.get("classifier_guidance", {})
    return guidance.get("multi_match_resolution", "prefer most specific signals")


def get_unknown_threshold(taxonomy: dict[str, Any]) -> float:
    """Get unknown_share_threshold."""
    return float(taxonomy.get("unknown_share_threshold", 0.15))
