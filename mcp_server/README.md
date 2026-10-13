# Campus Customs MCP server

This [FastMCP](https://gofastmcp.com) server is the only way the HW 5 agents (Boss, Inventory, Accounting, Facilities, Customer Service) reach Campus Customs shop data. Agents never run SQL themselves; they call these tools instead. Read tools return only values stored in the database, plus arithmetic on them. If a row doesn't exist, the tool returns `"found": false` and a message rather than making up a value. Write tools take amounts and dates from the database, never from the caller.

**Database:** [`../data/campus_customs_new.db`](../data/campus_customs_new.db), the working copy. Set `CAMPUS_CUSTOMS_DB` to point at a different copy, such as a scratch DB for tests. The server never touches the original `campus_customs.db`.

## Tools

| Tool | Tables | Returns / does |
| --- | --- | --- |
| `get_shop_date()` | `desk` | The shop's "today" (2026-08-31) and desk notes |
| `list_open_tickets()` | `tickets` | Every ticket not yet `resolved` |
| `get_ticket(ticket_id)` | `tickets` | One ticket with all its fields |
| `get_stock_for_sku_and_size(sku, size)` | `inventory` | Quantity and aisle for that SKU and size, plus every other size of the same SKU |
| `list_vendors()` | `vendors` | Vendors with their specialty and lead days |
| `get_invoice_and_vendor(invoice_id)` | `invoices`, `vendors`, `desk` | The invoice, its vendor, and `days_overdue` |
| `get_rent_due_and_cash_balance(lease_id)` | `leases`, `cash_accounts`, `desk` | Rent amount, landlord, due date, days until due, and cash balances |
| `list_leases()` | `leases`, `desk` | Every lease with rent, next due date, and days until due |
| `get_unit_cost_and_list_price(sku)` | `pricing` | Unit cost (the lowest price allowed with any discount) and list price |
| `quote_price_for_quantity(sku, qty, discount_percent)` | `pricing` | Discounted unit price, totals, margin, and a `below_cost` flag (saves nothing) |
| `list_payments(kind?, ref_id?)` | `payments` | Recorded payments, for checking whether something is already paid |
| `list_tickets()` | `tickets` | Every ticket, any status (for the dashboard) |
| `get_cash_balance(account='checking')` | `cash_accounts` | One account's balance and as-of date |
| `request_payment_approval(ticket_id, kind, ref_id, account, reason, requested_by)` | writes `payment_requests` | Prepares a payment for a person to approve; **moves no money**. The amount comes from the DB. Refuses things that can't be paid, and duplicates of a pending request |
| `list_payment_requests(status?, ticket_id?)` | `payment_requests` | Pending, approved, or rejected requests |
| `approve_payment_request(request_id, approved_by, note?)` | writes `payment_requests`, `payments`, `cash_accounts`, `invoices` | **The only tool that moves cash.** Re-checks the request, then pays it. Called only by the API's approve route |
| `reject_payment_request(request_id, rejected_by, reason)` | writes `payment_requests` | Marks a request rejected |
| `update_ticket(ticket_id, status, note, author)` | writes `tickets` | Sets the status and appends a dated, signed note (earlier notes are kept) |

The agent harness ([`../backend/team.py`](../backend/team.py)) gives each agent only its own subset of these tools. It also fills in `ticket_id`/`requested_by` and `author` itself, so a model can't set them. No agent may call `approve_payment_request` or `reject_payment_request`; only the dashboard API ([`../backend/main.py`](../backend/main.py)) calls them, after a person acts.

## Run

From the `HW 5` folder:

```bash
.venv/bin/python mcp_server/server.py
```

This uses the stdio transport. The agent backend starts it the same way, through `backend/run.py` or the FastAPI app in `backend/main.py`.

## Connection

To call the tools from Claude Code (or any MCP client), register the server in that project's `.mcp.json` with this repo's venv Python. Replace `<repo>` with the absolute path to your clone:

```json
"campus-customs": {
  "command": "<repo>/.venv/bin/python",
  "args": ["<repo>/mcp_server/server.py"]
}
```

Claude Code loads it in new sessions started from `my-app` (approve it when prompted). Test results are in [`../output/mcp_smoke.json`](../output/mcp_smoke.json).
