"""eval — Terminal-Bench Dev Set v2 пайплайн оценки продукта.

Живёт в родителе (vsmlite-tb): знает про Terminal Bench, скачивает датасет с HF,
запускает продукт (../src/ — failure-aware harness) на TB-задачах внутри Docker
песочниц, честно грейдит outcome-based pytest'ами, пишет pass-rate в
state/dev_metrics.json как метрику автономности A(t) (VSM-004/005).

Мембрана (VSM-002): продукт НЕ модифицируется и не знает про оценку.
../src/mcp_server/ монтируется read-only и запускается как subprocess внутри
контейнера (docker-exec MCP bridge). task_prompt нейтрализуется membrane.py
перед пересечением границы.
"""
from .config import EvalConfig
from .loader import TBTask, download, load_tasks, list_tasks

__all__ = ["EvalConfig", "TBTask", "download", "load_tasks", "list_tasks"]
