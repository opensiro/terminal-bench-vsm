"""filesystem tools — read/write/edit/list/glob/grep."""
from __future__ import annotations
import fnmatch
import os
import re
import time
from pathlib import Path


def register_filesystem_tools(server, workspace: str):
    ws = Path(workspace).resolve()

    def _safe_path(p: str) -> Path:
        resolved = (ws / p).resolve()
        if not str(resolved).startswith(str(ws)):
            raise ValueError(f"path outside workspace: {p}")
        return resolved

    def fs_read(path: str) -> dict:
        start = time.time()
        p = _safe_path(path)
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            return {"stdout": content, "stderr": "", "exit_code": 0, "time_seconds": time.time() - start}
        except FileNotFoundError:
            return {"stdout": "", "stderr": f"file not found: {path}", "exit_code": 1, "time_seconds": time.time() - start}

    def fs_write(path: str, content: str) -> dict:
        start = time.time()
        p = _safe_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"stdout": f"wrote {len(content)} bytes to {path}", "stderr": "", "exit_code": 0, "time_seconds": time.time() - start}

    def fs_edit(path: str, old_string: str, new_string: str) -> dict:
        start = time.time()
        p = _safe_path(path)
        try:
            text = p.read_text(encoding="utf-8")
            if old_string not in text:
                return {"stdout": "", "stderr": "old_string not found", "exit_code": 1, "time_seconds": time.time() - start}
            count = text.count(old_string)
            text = text.replace(old_string, new_string)
            p.write_text(text, encoding="utf-8")
            return {"stdout": f"replaced {count} occurrence(s)", "stderr": "", "exit_code": 0, "time_seconds": time.time() - start}
        except FileNotFoundError:
            return {"stdout": "", "stderr": f"file not found: {path}", "exit_code": 1, "time_seconds": time.time() - start}

    def fs_list(path: str = ".") -> dict:
        start = time.time()
        p = _safe_path(path)
        try:
            entries = sorted([e.name for e in p.iterdir()])
            return {"stdout": "\n".join(entries), "stderr": "", "exit_code": 0, "time_seconds": time.time() - start}
        except FileNotFoundError:
            return {"stdout": "", "stderr": f"not found: {path}", "exit_code": 1, "time_seconds": time.time() - start}

    def fs_glob(pattern: str, path: str = ".") -> dict:
        start = time.time()
        p = _safe_path(path)
        matches = []
        for root, dirs, files in os.walk(p):
            for f in files:
                if fnmatch.fnmatch(f, pattern):
                    matches.append(str(Path(root).relative_to(ws) / f))
        return {"stdout": "\n".join(sorted(matches)), "stderr": "", "exit_code": 0, "time_seconds": time.time() - start}

    def fs_grep(pattern: str, path: str = ".") -> dict:
        start = time.time()
        p = _safe_path(path)
        regex = re.compile(pattern)
        matches = []
        for root, dirs, files in os.walk(p):
            for f in files:
                fp = Path(root) / f
                try:
                    for i, line in enumerate(fp.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                        if regex.search(line):
                            matches.append(f"{fp.relative_to(ws)}:{i}: {line.strip()}")
                except (OSError, UnicodeDecodeError):
                    pass
        return {"stdout": "\n".join(matches[:100]), "stderr": "", "exit_code": 0, "time_seconds": time.time() - start}

    server.register("fs.read", "read file", {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, fs_read)
    server.register("fs.write", "write file", {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}, fs_write)
    server.register("fs.edit", "edit file (string replace)", {"type": "object", "properties": {"path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, "required": ["path", "old_string", "new_string"]}, fs_edit)
    server.register("fs.list", "list directory", {"type": "object", "properties": {"path": {"type": "string", "default": "."}}}, fs_list)
    server.register("fs.glob", "glob files", {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string", "default": "."}}}, fs_glob)
    server.register("fs.grep", "grep content", {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string", "default": "."}}}, fs_grep)
