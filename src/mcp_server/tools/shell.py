"""shell tools — exec with mandatory timeout."""
from __future__ import annotations
import subprocess
import time


def register_shell_tools(server, workspace: str):
    def shell_exec(command: str, cwd: str = ".", timeout: int = 30) -> dict:
        start = time.time()
        try:
            result = subprocess.run(
                command, shell=True, cwd=workspace + "/" + cwd,
                capture_output=True, text=True, timeout=timeout,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "time_seconds": time.time() - start,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"command timed out after {timeout}s",
                "exit_code": 124,
                "time_seconds": float(timeout),
            }

    server.register(
        "shell.exec",
        "execute shell command (with mandatory timeout)",
        {"type": "object", "properties": {"command": {"type": "string"}, "cwd": {"type": "string", "default": "."}, "timeout": {"type": "integer", "default": 30}}, "required": ["command"]},
        shell_exec,
    )
