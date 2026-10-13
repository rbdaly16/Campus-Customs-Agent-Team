"""Customer Service agent: drafts accurate replies to requesters; never sends them and never shares internal numbers."""

from models import AgentReport
from team import build_agent

MCP_TOOLS = {"get_shop_date", "get_ticket", "get_stock_for_sku_and_size"}

agent = build_agent("customer_service", MCP_TOOLS, AgentReport)
