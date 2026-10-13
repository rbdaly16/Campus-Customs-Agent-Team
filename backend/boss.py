"""Boss agent: reads one ticket, delegates to the specialists, and records the final decision."""

from models import TicketOutcome
from team import build_agent

MCP_TOOLS = {"get_shop_date", "list_open_tickets", "get_ticket", "update_ticket"}

agent = build_agent("boss", MCP_TOOLS, TicketOutcome)
