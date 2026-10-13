"""Inventory agent: stock on hand, in-stock alternatives, shortfalls, and restock vendors and lead times."""

from models import AgentReport
from team import build_agent

MCP_TOOLS = {"get_shop_date", "get_ticket", "get_stock_for_sku_and_size", "list_vendors", "get_invoice_and_vendor"}

agent = build_agent("inventory", MCP_TOOLS, AgentReport)
