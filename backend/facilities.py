"""Facilities agent: the lease and landlord; checks rent notices against the lease before anyone pays."""

from models import AgentReport
from team import build_agent

MCP_TOOLS = {"get_shop_date", "get_ticket", "get_rent_due_and_cash_balance", "list_payments"}

agent = build_agent("facilities", MCP_TOOLS, AgentReport)
