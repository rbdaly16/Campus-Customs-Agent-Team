"""FastAPI backend for the Campus Customs desk dashboard.

From the backend/ folder (with the HW 5 venv active):
  uvicorn main:app --reload --port 8000

Shop data goes through the same campus-customs MCP server the agents use; this file has no SQL.
Agents only *prepare* payments; POST /approvals/{id}/approve is the one place cash changes,
and only after a person clicks approve. Every human action is appended to the audit trail.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import accounting, boss, customer_service, facilities, inventory  # noqa: F401  (registers the agents)
import audit
import team
from models import AuditEntry

ORIGINAL_DB = team.HW_DIR / "data" / "campus_customs.db"
# Overridable so tests can point at scratch copies instead of the real working DB and trail.
WORKING_DB = Path(os.environ.get("CAMPUS_CUSTOMS_DB", team.DEFAULT_DB)).resolve()
AUDIT_PATH = Path(os.environ.get("AUDIT_TRAIL_PATH", audit.DEFAULT_PATH)).resolve()

# Runs started from the dashboard: run_id -> status. In memory; the audit trail is the durable record.
RUNS: dict[str, dict[str, Any]] = {}
_tasks: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with team.connect_mcp(WORKING_DB):
        yield
    for task in _tasks:
        task.cancel()


app = FastAPI(title="Campus Customs desk API", lifespan=lifespan)
# The Vite dev page (npm run dev) is http://localhost:5173. If that port is taken Vite moves to the
# next one, so other local ports are allowed too; nothing outside this machine is.
FRONTEND_ORIGINS = os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------- helpers


async def mcp(tool: str, **args: Any) -> Any:
    """Call a campus-customs MCP tool directly (no agent) and return its parsed result."""
    return await team.mcp_toolset().direct_call_tool(tool, args)


def human_audit(event: str, ticket_id: int | None, actor: str, **detail: Any) -> None:
    """Record a dashboard action (approval, reset, run request) in the same append-only trail."""
    audit.append(
        AUDIT_PATH,
        AuditEntry(
            time=audit.now(), run_id="dashboard", ticket_id=ticket_id, agent="human", agent_run_id="-",
            parent=None, depth=0, event=event, detail={"by": actor, **detail},
        ),
    )


def running_tickets() -> set[int]:
    return {r["ticket_id"] for r in RUNS.values() if r["status"] == "running"}


def read_audit() -> list[dict]:
    if not AUDIT_PATH.exists():
        return []
    return json.loads(AUDIT_PATH.read_text())


def event_view(index: int, e: dict) -> dict:
    """Flatten an audit entry into what the board shows: who, what they said, which tools."""
    d = e.get("detail", {})
    said, tools = None, []
    if e["event"] == "loop_model_response":
        said = d.get("text")
        tools = [c["tool"] for c in d.get("tool_calls", []) if c["tool"] != "final_result"]
    elif e["event"] in ("mcp_tool_call", "mcp_tool_blocked", "mcp_tool_error"):
        tools = [d.get("tool")]
    elif e["event"] == "delegation":
        said = f"→ {d.get('to')}: {audit.short(d.get('task', ''), 300)}"
        tools = ["delegate"]
    elif e["event"] == "agent_end":
        out = d.get("output", {})
        said = out.get("decision") or out.get("summary")
    elif e["agent"] == "human":
        said = f"{e['event'].replace('_', ' ')} by {d.get('by')}" + (
            f" (request #{d['request_id']})" if "request_id" in d else ""
        )
    return {
        "index": index,
        "time": e["time"],
        "run_id": e["run_id"],
        "ticket_id": e["ticket_id"],
        "agent": e["agent"],
        "parent": e.get("parent"),
        "step": e.get("step"),
        "event": e["event"],
        "said": said,
        "tools": tools,
        "detail": d,
    }


async def _run_in_background(run_id: str, ticket_id: int) -> None:
    run = RUNS[run_id]
    try:
        outcome = await team.run_ticket(ticket_id, run_id, AUDIT_PATH)
        run.update(status="done", outcome=outcome.model_dump())
    except Exception as e:
        run.update(status="error", error=f"{type(e).__name__}: {e}")
    finally:
        run["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- request bodies


class ApproveBody(BaseModel):
    approved_by: str = Field(min_length=1, description="Name of the person who clicked approve")
    note: str = ""
    resolve_ticket: bool = Field(False, description="Also mark the ticket resolved if nothing else is pending")


class CloseBody(BaseModel):
    closed_by: str = Field(min_length=1, description="Name of the person closing the ticket")
    note: str = ""


class RejectBody(BaseModel):
    rejected_by: str = Field(min_length=1)
    reason: str = ""


class ResetBody(BaseModel):
    reset_by: str = "dashboard"


# ---------------------------------------------------------------- routes


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "db": str(WORKING_DB), "model": team.MODEL_NAME}


@app.get("/tickets")
async def list_tickets() -> dict:
    """Every ticket with its DB status and a board `state`: open (crew hasn't worked it), running
    (agents working now), awaiting_human (a person must act: approve, send a reply, ...),
    waiting_on_customer, or resolved (nothing left for anyone)."""
    res = await mcp("list_tickets")
    pending = (await mcp("list_payment_requests", status="pending"))["requests"]
    busy = running_tickets()
    tickets = []
    for t in res["tickets"]:
        if t["id"] in busy:
            state = "running"
        elif t["status"] in ("open", "in_progress"):
            state = "open"
        elif t["status"] == "resolved":
            state = "resolved"
        elif t["status"] == "waiting_on_customer":
            state = "waiting_on_customer"
        else:
            state = "awaiting_human"
        tickets.append({
            **t, "state": state, "agents_running": t["id"] in busy,
            "pending_approvals": sum(r["ticket_id"] == t["id"] for r in pending),
        })
    return {"tickets": tickets}


@app.post("/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(ticket_id: int) -> dict:
    """Start the agent team on one ticket. Returns at once; poll /runs/{run_id} or /events."""
    ticket = await mcp("get_ticket", ticket_id=ticket_id)
    if not ticket["found"]:
        raise HTTPException(404, ticket["message"])
    if ticket_id in running_tickets():
        raise HTTPException(409, f"Agents are already working on ticket {ticket_id}.")
    run_id = uuid.uuid4().hex[:12]
    RUNS[run_id] = {
        "run_id": run_id, "ticket_id": ticket_id, "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    task = asyncio.create_task(_run_in_background(run_id, ticket_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return RUNS[run_id]


@app.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    """Status of a dashboard run: running, done (with the Boss's outcome), or error."""
    if run_id not in RUNS:
        raise HTTPException(404, f"No run {run_id} in this server session.")
    return RUNS[run_id]


@app.get("/tickets/{ticket_id}/summary")
async def ticket_summary(ticket_id: int) -> dict:
    """What each agent did on the ticket's most recent run: its own summary, tools, and hand-offs."""
    entries = [e for e in read_audit() if e["ticket_id"] == ticket_id]
    starts = [e for e in entries if e["event"] == "ticket_start"]
    if not starts:
        return {"ticket_id": ticket_id, "run_id": None, "status": "never_run", "outcome": None, "agents": []}
    run_id = starts[-1]["run_id"]
    run = [e for e in entries if e["run_id"] == run_id]
    agents: dict[str, dict] = {}
    for e in run:
        if e["agent"] == "human":
            continue
        a = agents.setdefault(e["agent"], {
            "agent": e["agent"], "times_called": 0, "summary": None, "tools": [], "handed_to": [],
            "actions": [], "needs_human": [], "customer_message": None,
        })
        d = e["detail"]
        if e["event"] == "agent_start":
            a["times_called"] += 1
        elif e["event"] == "mcp_tool_call" and d["tool"] not in a["tools"]:
            a["tools"].append(d["tool"])
        elif e["event"] == "delegation":
            a["handed_to"].append(d["to"])
        elif e["event"] == "agent_end":
            out = d["output"]
            a["summary"] = out.get("decision") or out.get("summary")
            a["actions"] = out.get("actions_taken", [])
            a["needs_human"] = out.get("needs_human", [])
            a["customer_message"] = out.get("customer_message") or a["customer_message"]
    boss_end = [e for e in run if e["agent"] == "boss" and e["event"] == "agent_end" and e["depth"] == 0]
    errors = [e for e in run if e["event"] == "ticket_error"]
    status = "done" if boss_end else "error" if errors else "running"
    return {
        "ticket_id": ticket_id, "run_id": run_id, "status": status,
        "started_at": starts[-1]["time"], "finished_at": (boss_end or errors or [{}])[-1].get("time"),
        "outcome": boss_end[-1]["detail"]["output"] if boss_end else None,
        "error": errors[-1]["detail"].get("error") if errors and not boss_end else None,
        "agents": list(agents.values()),
    }


@app.get("/events")
async def events(
    after: int = Query(-1, description="Only events with index greater than this (for incremental refresh)"),
    ticket_id: int | None = None,
    run_id: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
) -> dict:
    """Recent audit events: what each agent said and which tools it used."""
    entries = read_audit()
    views = [
        event_view(i, e) for i, e in enumerate(entries)
        if i > after and (ticket_id is None or e["ticket_id"] == ticket_id) and (run_id is None or e["run_id"] == run_id)
    ]
    return {"next_after": len(entries) - 1, "events": views[-limit:]}


@app.get("/approvals")
async def approvals(status: Literal["pending", "approved", "rejected"] | None = "pending") -> dict:
    """Payment requests the agents prepared (pending by default)."""
    return await mcp("list_payment_requests", status=status)


@app.post("/approvals/{request_id}/approve")
async def approve(request_id: int, body: ApproveBody) -> dict:
    """A person approved this payment: pay it (the only route that changes cash)."""
    res = await mcp("approve_payment_request", request_id=request_id, approved_by=body.approved_by, note=body.note)
    human_audit("payment_approved" if res["ok"] else "payment_approval_failed", res.get("ticket_id"),
                body.approved_by, request_id=request_id, result=res)
    if not res["ok"]:
        raise HTTPException(409, res["message"])
    ticket_id = res["ticket_id"]
    if ticket_id is not None:
        still_pending = (await mcp("list_payment_requests", status="pending", ticket_id=ticket_id))["count"]
        ticket = (await mcp("get_ticket", ticket_id=ticket_id))["ticket"]
        status = ticket["status"]
        # Only the approver can say nothing else is left (e.g. a reply still to send); otherwise
        # the ticket stays awaiting_human_input.
        if body.resolve_ticket and not still_pending:
            status = "resolved"
        res["ticket"] = await mcp(
            "update_ticket", ticket_id=ticket_id, status=status, author=body.approved_by,
            note=f"Approved payment request #{request_id}: ${res['amount']:,.2f} {res['kind']} "
                 f"(payment #{res['payment_id']}). {res['account']} balance now ${res['balance_after']:,.2f}.",
        )
    return res


@app.post("/approvals/{request_id}/reject")
async def reject(request_id: int, body: RejectBody) -> dict:
    """A person rejected this payment request. No money moves."""
    res = await mcp("reject_payment_request", request_id=request_id, rejected_by=body.rejected_by, reason=body.reason)
    human_audit("payment_rejected" if res["ok"] else "payment_rejection_failed", res.get("ticket_id"),
                body.rejected_by, request_id=request_id, reason=body.reason, result=res)
    if not res["ok"]:
        raise HTTPException(409, res["message"])
    return res


@app.post("/tickets/{ticket_id}/close")
async def close_ticket(ticket_id: int, body: CloseBody) -> dict:
    """A person confirms they finished the human steps (sent the reply, etc.); the ticket becomes resolved.
    Refused while agents run, before the crew has worked it, or while a payment is still undecided."""
    if ticket_id in running_tickets():
        raise HTTPException(409, f"Agents are still working on ticket {ticket_id}.")
    found = await mcp("get_ticket", ticket_id=ticket_id)
    if not found["found"]:
        raise HTTPException(404, found["message"])
    if found["ticket"]["status"] == "open":
        raise HTTPException(409, "The crew hasn't worked this ticket yet; send the crew first.")
    if (await mcp("list_payment_requests", status="pending", ticket_id=ticket_id))["count"]:
        raise HTTPException(409, "A payment request on this ticket is still waiting for a decision.")
    note = body.note.strip() or "Closed by a person on the Coral Desk."
    res = await mcp("update_ticket", ticket_id=ticket_id, status="resolved", note=note, author=body.closed_by)
    human_audit("ticket_closed", ticket_id, body.closed_by, note=note, result=res)
    return res


@app.get("/cash")
async def cash() -> dict:
    """Current checking balance from cash_accounts."""
    res = await mcp("get_cash_balance", account="checking")
    if not res["found"]:
        raise HTTPException(404, res["message"])
    return res


@app.post("/reset")
async def reset(body: ResetBody | None = None) -> dict:
    """Restore campus_customs_new.db from the original campus_customs.db for a fresh run.

    The audit trail is NOT wiped (it is append-only); the reset itself is recorded in it.
    """
    if running_tickets():
        raise HTTPException(409, "Agents are still running; wait for them to finish before resetting.")
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    human_audit("db_reset", None, (body or ResetBody()).reset_by, source=ORIGINAL_DB.name, target=WORKING_DB.name)
    return {"ok": True, "message": f"{WORKING_DB.name} restored from {ORIGINAL_DB.name}.", "cash": await cash()}
