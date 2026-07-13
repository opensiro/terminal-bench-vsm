"""InstallDependency — установить модуль через менеджер пакетов языка (ImportError)."""
from __future__ import annotations
import subprocess
from .base import RecoveryContext, RecoveryResult

# Маппинг import-name → package-name для известных расхождений
_IMPORT_TO_PACKAGE = {
    "PIL": "Pillow", "cv2": "opencv-python", "sklearn": "scikit-learn",
    "yaml": "PyYAML", "bs4": "beautifulsoup4", "jwt": "PyJWT",
    "Crypto": "pycryptodome", "magic": "python-magic",
}


def apply(ctx: RecoveryContext) -> RecoveryResult:
    module_name = ctx.extra.get("module_name")
    if not module_name:
        # Пытаемся извлечь из failure_observations
        for obs in ctx.failure_observations:
            val = obs.get("value", "")
            if "No module named" in val:
                parts = val.split("'")
                if len(parts) >= 2:
                    module_name = parts[1].split(".")[0]
                    break
    if not module_name:
        return RecoveryResult(blocked="missing module_name")
    package_name = ctx.extra.get("package_name") or _IMPORT_TO_PACKAGE.get(module_name, module_name)
    pip_path = "pip3"
    try:
        subprocess.run([pip_path, "install", package_name], check=True, capture_output=True, timeout=120)
        return RecoveryResult(applied=True, env_changes=[f"installed: {package_name} (pip)"])
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        return RecoveryResult(blocked=f"pip install {package_name} failed: {exc}")
