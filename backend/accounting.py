"""Accounting agent: prices and discount policy, cash, vendor invoices, and the only agent that can request payments."""

from models import AgentReport
from team import build_agent

MCP_TOOLS = {
    "get_shop_date",
    "get_ticket",
    "get_unit_cost_and_list_price",
    "quote_price_for_quantity",
    "get_rent_due_and_cash_balance",
    "get_cash_balance",
    "list_leases",
    "get_invoice_and_vendor",
    "list_payments",
    "request_payment_approval",
    "list_payment_requests",
}

agent = build_agent("accounting", MCP_TOOLS, AgentReport)
