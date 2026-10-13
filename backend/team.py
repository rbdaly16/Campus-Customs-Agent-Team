"""Shared wiring for the Campus Customs agent team.

- One model for every agent: gpt-6-luna through Portkey.
- One MCP connection (mcp_server/server.py over stdio). Each agent sees only its allowlisted
  MCP tools; there is no other path to shop data.
- A `delegate` tool on every agent, so any agent can hand work to any other (full connectivity),
  bounded by the TeamBudget depth/count caps and by never re-entering the current chain.
- `run_ticket` is the one entry point (CLI and API) for the Boss to work a ticket.
- `run_agent` drives the agent loop with `Agent.iter` and appends one audit entry per loop step;
  the MCP hook appends one per tool call.
"""

from __future__ import annotations

import asyncio
import copy
import dataclasses
import os
import sys
import time
from functools import cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastmcp.client.transports import PythonStdioTransport
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import CallToolFunc, MCPToolset
from pydantic_ai.messages import RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.usage import RunUsage, UsageLimits

import audit
from models import AgentName, ShopDeps, TeamBudget

BACKEND_DIR = Path(__file__).resolve().parent
HW_DIR = BACKEND_DIR.parent
PROMPTS_DIR = BACKEND_DIR / "prompts"
SERVER_PATH = HW_DIR / "mcp_server" / "server.py"
DEFAULT_DB = HW_DIR / "data" / "campus_customs_new.db"

# PORTKEY_API_KEY: this homework's .env if present, else the course repo's shared root .env.
load_dotenv(HW_DIR / ".env")
load_dotenv(HW_DIR.parent / ".env")
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
# Responses API: the Portkey/Azure deployment rejects function tools + reasoning on /chat/completions.
# openai_store=False keeps ticket data out of provider-side storage.
MODEL_SETTINGS = OpenAIResponsesModelSettings(max_tokens=4000, parallel_tool_calls=False, openai_store=False)
# One budget per ticket, shared by every agent that works on it (sub-runs reuse the parent's usage).
TEAM_LIMITS = UsageLimits(request_limit=40, tool_calls_limit=60, total_tokens_limit=300_000)

# Arguments the harness fills in (and hides from the model), so an agent can't sign as someone
# else or file a request against a different ticket.
HARNESS_ARGS = {
    "request_payment_approval": ("ticket_id", "requested_by"),
    "update_ticket": ("author",),
}
# Tools that move money or decide approvals. No agent may ever call these; only the API's
# human-approval routes do.
HUMAN_ONLY_TOOLS = frozenset({"approve_payment_request", "reject_payment_request"})
TICKET_TIMEOUT_S = 600  # wall-clock cap per ticket so a hung model call fails cleanly

REGISTRY: dict[str, Agent[ShopDeps, Any]] = {}
AGENT_MCP_TOOLS: dict[str, frozenset[str]] = {}
_mcp: MCPToolset | None = None
_db_path: Path = DEFAULT_DB


@cache
def _model() -> OpenAIResponsesModel:
    key = os.environ.get("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set (expected in the repo root .env).")
    client = AsyncOpenAI(api_key=key, base_url=PORTKEY_BASE_URL, timeout=120, max_retries=2)
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


# ---------------------------------------------------------------- MCP


def connect_mcp(db_path: Path = DEFAULT_DB) -> MCPToolset:
    """Create the single MCP connection all agents share. Enter it with `async with` before running."""
    global _mcp, _db_path
    _db_path = db_path
    transport = PythonStdioTransport(SERVER_PATH, env={"CAMPUS_CUSTOMS_DB": str(db_path)}, python_cmd=sys.executable)
    _mcp = MCPToolset(transport, process_tool_call=_guard_and_audit, max_retries=1)
    return _mcp


async def _guard_and_audit(ctx: RunContext[ShopDeps], call_tool: CallToolFunc, name: str, args: dict[str, Any]) -> Any:
    """Every MCP call passes through here: enforce the allowlist (and that no agent can move
    money), fill harness-owned arguments, and audit the call with its result."""
    deps = ctx.deps
    if name in HUMAN_ONLY_TOOLS or name not in AGENT_MCP_TOOLS[deps.agent]:
        blocked = f"{deps.agent} is not allowed to call {name}."
        audit.record(deps, "mcp_tool_blocked", step=deps.step, tool=name, args=args, reason=blocked)
        return {"ok": False, "blocked": blocked}

    if name == "request_payment_approval":
        args = {**args, "ticket_id": deps.ticket_id, "requested_by": f"{deps.agent} agent"}
    elif name == "update_ticket":
        args = {**args, "author": f"{deps.agent} agent"}
    start = time.perf_counter()
    try:
        result = await call_tool(name, args)
    except Exception as e:
        audit.record(deps, "mcp_tool_error", step=deps.step, tool=name, args=args, error=audit.short(str(e)))
        raise
    audit.record(
        deps, "mcp_tool_call", step=deps.step, tool=name, args=args,
        result=audit.short(result), ms=round((time.perf_counter() - start) * 1000),
    )
    return result


def _hide_harness_args(ctx: RunContext[ShopDeps], tool_defs: list[ToolDefinition]) -> list[ToolDefinition]:
    """Drop harness-owned arguments from the schemas the model sees."""
    out = []
    for td in tool_defs:
        hidden = HARNESS_ARGS.get(td.name)
        if hidden:
            schema = copy.deepcopy(td.parameters_json_schema)
            for arg in hidden:
                schema.get("properties", {}).pop(arg, None)
            schema["required"] = [r for r in schema.get("required", []) if r not in hidden]
            td = dataclasses.replace(td, parameters_json_schema=schema)
        out.append(td)
    return out


def mcp_toolset() -> MCPToolset:
    """The shared MCP connection, for non-agent callers such as the API routes."""
    if _mcp is None:
        raise RuntimeError("Call team.connect_mcp() first.")
    return _mcp


def _toolset_for(name: str):
    if _mcp is None:
        raise RuntimeError("Call team.connect_mcp() before running agents.")
    allowed = AGENT_MCP_TOOLS[name]
    return _mcp.filtered(lambda ctx, td: td.name in allowed).prepared(_hide_harness_args)


# ---------------------------------------------------------------- delegation


async def delegate(ctx: RunContext[ShopDeps], teammate: AgentName, task: str) -> dict:
    """Hand a sub-task to a teammate agent and get its structured report back.

    Args:
        teammate: boss, inventory, accounting, facilities, or customer_service.
        task: Self-contained instructions: the ticket id, the exact SKU/size/qty or lease/invoice
            ids, the question to answer, and any facts already confirmed. The teammate cannot
            see your conversation.
    """
    d, budget = ctx.deps, ctx.deps.budget
    if teammate == d.agent:
        reason = "You can't delegate to yourself."
    elif teammate in d.chain:
        reason = f"{teammate} is already waiting on this request ({' -> '.join(d.chain)}); answer with what you have."
    elif d.depth >= budget.max_depth:
        reason = f"Delegation depth limit ({budget.max_depth}) reached; answer with what you have."
    elif budget.used >= budget.max_delegations:
        reason = f"This ticket has used all {budget.max_delegations} delegations; answer with what you have."
    else:
        reason = None
    if reason:
        audit.record(d, "delegation_refused", step=d.step, to=teammate, task=audit.short(task), reason=reason)
        return {"refused": reason}

    budget.used += 1
    audit.record(d, "delegation", step=d.step, to=teammate, task=task, delegations_used=budget.used)
    report = await run_agent(teammate, task, d.child(teammate), usage=ctx.usage)
    return report.model_dump()


# ---------------------------------------------------------------- agents


def build_agent(name: AgentName, mcp_tools: set[str], output_type: type[BaseModel]) -> Agent[ShopDeps, Any]:
    """Create an agent from prompts/<name>.md with its MCP allowlist and the delegate tool."""
    agent = Agent(
        _model(),
        name=name,
        deps_type=ShopDeps,
        output_type=output_type,
        instructions=(PROMPTS_DIR / f"{name}.md").read_text(),
        tools=[delegate],
        model_settings=MODEL_SETTINGS,
        retries=2,
    )

    @agent.instructions
    def run_context(ctx: RunContext[ShopDeps]) -> str:
        d, b = ctx.deps, ctx.deps.budget
        lines = [
            f"Ticket in scope: {d.ticket_id}.",
            f"Delegation path so far: {' -> '.join(d.chain)}. You can't delegate to anyone already on it.",
            f"Delegations left for this ticket: {b.max_delegations - b.used}. Depth left: {b.max_depth - d.depth}.",
        ]
        lines.append(
            "No agent can move money. Accounting prepares payments with request_payment_approval; "
            "a person approves or rejects them on the dashboard."
        )
        return "\n".join(lines)

    REGISTRY[name] = agent
    AGENT_MCP_TOOLS[name] = frozenset(mcp_tools)
    return agent


async def run_agent(name: AgentName, task: str, deps: ShopDeps, usage: RunUsage | None = None) -> Any:
    """Run one agent loop to completion, auditing every step. Returns the agent's typed output."""
    agent = REGISTRY[name]
    audit.record(deps, "agent_start", task=task, model=MODEL_NAME, prompt_file=f"backend/prompts/{name}.md")
    try:
        async with agent.iter(task, deps=deps, usage=usage, usage_limits=TEAM_LIMITS, toolsets=[_toolset_for(name)]) as run:
            async for node in run:
                deps.step += 1
                _audit_node(deps, deps.step, node)
    except Exception as e:
        audit.record(deps, "agent_error", step=deps.step, error=f"{type(e).__name__}: {audit.short(str(e))}")
        raise
    u = run.usage
    audit.record(
        deps, "agent_end", step=deps.step, output=run.result.output.model_dump(),
        team_usage={"requests": u.requests, "tool_calls": u.tool_calls,
                    "input_tokens": u.input_tokens, "output_tokens": u.output_tokens},
    )
    return run.result.output


def _audit_node(deps: ShopDeps, step: int, node: Any) -> None:
    """One audit entry per agent-loop node: what went to the model, what came back, and the end."""
    if Agent.is_user_prompt_node(node):
        audit.record(deps, "loop_user_prompt", step=step, prompt=audit.short(node.user_prompt))
    elif Agent.is_model_request_node(node):
        sends = []
        for p in node.request.parts:
            if isinstance(p, ToolReturnPart):
                sends.append({"tool_return": p.tool_name, "content": audit.short(p.content)})
            elif isinstance(p, RetryPromptPart):
                sends.append({"retry": p.tool_name, "reason": audit.short(p.content)})
            elif isinstance(p, UserPromptPart):
                sends.append({"user_prompt": audit.short(p.content)})
        audit.record(deps, "loop_model_request", step=step, sends=sends)
    elif Agent.is_call_tools_node(node):
        r = node.model_response
        text = " ".join(p.content for p in r.parts if isinstance(p, TextPart))
        audit.record(
            deps, "loop_model_response", step=step, model=r.model_name, finish_reason=r.finish_reason,
            text=audit.short(text) if text else None,
            tool_calls=[{"tool": p.tool_name, "args": audit.short(p.args_as_dict())} for p in r.parts if isinstance(p, ToolCallPart)],
            tokens={"input": r.usage.input_tokens, "output": r.usage.output_tokens},
        )
    elif Agent.is_end_node(node):
        audit.record(deps, "loop_end", step=step)


async def run_ticket(ticket_id: int, run_id: str, audit_path: Path = audit.DEFAULT_PATH) -> Any:
    """Have the Boss work one ticket end to end with a fresh team budget. Used by run.py and the API."""
    deps = ShopDeps(run_id, ticket_id, ("boss",), audit_path, TeamBudget())
    audit.record(deps, "ticket_start", model=MODEL_NAME, db=str(_db_path))
    try:
        return await asyncio.wait_for(
            run_agent("boss", f"Handle ticket {ticket_id}.", deps, usage=RunUsage()), TICKET_TIMEOUT_S
        )
    except BaseException as e:
        audit.record(deps, "ticket_error", error=f"{type(e).__name__}: {audit.short(str(e))}")
        raise
