"""Append-only audit trail: output/audit_trail.json.

The file is always a valid JSON array. Entries are written as they happen (one per agent-loop
step, MCP call, and delegation) by inserting them before the closing bracket, so earlier entries
are never rewritten and nothing here truncates or recreates an existing file. A file lock keeps
concurrent writers from interleaving.
"""

from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models import AuditEntry, ShopDeps

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
MAX_FIELD = 400  # args/results are trimmed summaries so the trail stays readable and small


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def short(value: Any, limit: int = MAX_FIELD) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str, separators=(",", ":"))
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def append(path: Path, entry: AuditEntry) -> None:
    """Insert one entry before the array's closing bracket without touching earlier entries."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(entry.model_dump(), ensure_ascii=False)
    with open(path, "a+b") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.seek(0, os.SEEK_END)
            if f.tell() == 0:
                f.write(f"[\n{body}\n]\n".encode())
                return
            tail_len = min(f.tell(), 64)
            f.seek(-tail_len, os.SEEK_END)
            tail = f.read(tail_len)
            close = tail.rfind(b"]")
            if close == -1:
                raise ValueError(f"{path} does not end with ']'; refusing to write")
            empty = tail[:close].rstrip().endswith(b"[")
            f.seek(-(tail_len - close), os.SEEK_END)
            f.truncate()  # removes only the closing "]\n"
            f.write((b"\n" if empty else b",\n") + body.encode() + b"\n]\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def record(deps: ShopDeps, event: str, step: int | None = None, **detail: Any) -> None:
    """Append an entry stamped with the agent run's identity and position in the delegation chain."""
    append(
        deps.audit_path,
        AuditEntry(
            time=now(),
            run_id=deps.run_id,
            ticket_id=deps.ticket_id,
            agent=deps.agent,
            agent_run_id=deps.agent_run_id,
            parent=deps.chain[-2] if len(deps.chain) > 1 else None,
            depth=deps.depth,
            step=step,
            event=event,
            detail=detail,
        ),
    )
