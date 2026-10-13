"""Data types shared by the Campus Customs agent team: run dependencies, agent outputs, audit entries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
TicketStatus = Literal["open", "in_progress", "awaiting_human_input", "waiting_on_customer", "resolved"]


# ---------------------------------------------------------------- agent outputs


class FactUsed(BaseModel):
    """One fact an agent relied on, and where it came from, so every claim can be traced."""

    source: str = Field(description="MCP tool name, or teammate name, that supplied the fact")
    fact: str = Field(description="The fact as stated by that source, with its numbers")


class AgentReport(BaseModel):
    """What a specialist (inventory, accounting, facilities, customer_service) hands back."""

    agent: AgentName
    summary: str = Field(description="Direct answer to the task, with key numbers")
    facts_used: list[FactUsed] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list, description="Writes actually performed, with record ids")
    recommendations: list[str] = Field(default_factory=list)
    needs_human: list[str] = Field(default_factory=list, description="Approvals or actions a person must take")
    customer_message: str | None = Field(default=None, description="Draft reply (customer_service only)")


class TicketOutcome(BaseModel):
    """The Boss's final decision on one ticket; mirrors what it wrote with update_ticket."""

    ticket_id: int
    final_status: TicketStatus
    decision: str
    actions_taken: list[str] = Field(default_factory=list)
    delegated_to: list[AgentName] = Field(default_factory=list)
    customer_message: str | None = None
    needs_human: list[str] = Field(default_factory=list)
    facts_used: list[FactUsed] = Field(default_factory=list)


# ---------------------------------------------------------------- run dependencies


@dataclass
class TeamBudget:
    """Delegation caps shared by every agent working one ticket (token caps live in UsageLimits)."""

    max_depth: int = 2  # boss -> specialist -> specialist, no deeper
    max_delegations: int = 5
    used: int = 0


@dataclass
class ShopDeps:
    """Per-agent-run context. `chain` is the delegation path, ending with this agent."""

    run_id: str
    ticket_id: int | None
    chain: tuple[AgentName, ...]
    audit_path: Path
    budget: TeamBudget
    agent_run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    step: int = 0  # current agent-loop step; tool calls and delegations are stamped with it

    @property
    def agent(self) -> AgentName:
        return self.chain[-1]

    @property
    def depth(self) -> int:
        return len(self.chain) - 1

    def child(self, teammate: AgentName) -> ShopDeps:
        return ShopDeps(self.run_id, self.ticket_id, (*self.chain, teammate), self.audit_path, self.budget)


# ---------------------------------------------------------------- audit


class AuditEntry(BaseModel):
    """One line in output/audit_trail.json: who did what, at which loop step, for which ticket."""

    time: str
    run_id: str
    ticket_id: int | None
    agent: str
    agent_run_id: str
    parent: str | None
    depth: int
    step: int | None = None
    event: str
    detail: dict[str, Any] = Field(default_factory=dict)
