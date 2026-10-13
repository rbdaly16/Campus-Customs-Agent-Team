# Campus Customs Agent Harness

This document describes the Campus Customs agent project for a manager: the data, the MCP tools, the five agents, the API routes, the dashboard, the safety rules, and the token limits. Everything listed here is implemented unless it is marked *not built*. The final run (Problem 9) is summarized at the end.

## Status

| Area | Status |
| --- | --- |
| Database study | Done (Problem 2) |
| MCP tools | 18 tools (14 read, 4 write); first 3 smoke-tested in Problem 4 |
| Backend API | Built (Problem 7): `backend/main.py`, FastAPI routes for the dashboard |
| Dashboard | Built (Problem 8): `frontend/` (React + Vite + TS), "The Coral Desk"; design in [`design.md`](design.md) |
| Agent team, entry point, loops | Built (Problem 5): Boss + 4 specialists, full delegation |
| Pydantic / PydanticAI models | Built (Problem 5) |
| Audit trail | Built (Problem 5): `output/audit_trail.json`, append-only |
| Safety and token limits | Built (Problem 5); extra guardrails listed as not built |
| Ticket plan vs. actual | `output/desk_tickets.html` (planned in Problem 6, actuals and cash filled in Problem 9) |
| Final run | Done (Problems 9/11): 102 resolved, 101 and 103 awaiting human input (replies to send); checking $3,400.00 → $160.00 ([`resolved_tickets.json`](resolved_tickets.json), [`resolved_board.html`](resolved_board.html)) |

## Data

- [`../data/campus_customs.db`](../data/campus_customs.db): the original database from the assignment zip. Read only; keep it unchanged.
- [`../data/campus_customs_new.db`](../data/campus_customs_new.db): the working copy. All writes go here, and `POST /reset` restores it from the original.

### Tables

The shop's "today" is **2026-08-31**, set by `desk.date_today`. Every due-date and overdue check should use this date, not the real clock.

**`desk`** (1 row): `date_today`, `notes`
Tells the agents what day it is in the shop, so they know what is due or overdue.

**`tickets`** (3 rows): `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at`
These are the agents' work queue. Each ticket says what was asked and links to the rows needed to act on it.

**`inventory`** (10 rows; key `sku` + `size`): `sku`, `name`, `size`, `qty`, `location`
Shows whether an order can be filled from stock, and from which aisle.

**`pricing`** (4 rows; key `sku`): `sku`, `unit_cost`, `list_price`
Gives the cost floor and the list price, so a discount agent can check margin before offering a price.

**`vendors`** (3 rows): `id`, `name`, `specialty`, `lead_days`
Shows who can restock or deliver an item and how long it takes, which sets the delivery dates customers are promised.

**`invoices`** (1 row; `vendor_id` → `vendors.id`): `id`, `vendor_id`, `amount`, `due_date`, `status`, `description`
Lists money the shop owes vendors. It also shows whether a restock has already been ordered.

**`leases`** (1 row): `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`
Records the shop's rent: how much, to whom, and when. It is used to check rent notices.

**`cash_accounts`** (1 row): `name`, `balance`, `date`
Shows how much cash is available, so agents never approve payments the shop can't cover.

**`payments`** (0 rows): `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`
This is the audit log for money going out. `kind` + `ref_id` point at the invoice or lease being paid, and `approved_by` records who signed off.

**`payment_requests`** (added by this project; created on first use, removed by reset): `id`, `ticket_id`, `kind`, `ref_id`, `amount`, `account`, `reason`, `requested_by`, `requested_at`, `status`, `decided_by`, `decided_at`, `decision_note`, `payment_id`
Holds payments the Accounting agent *prepared*, which wait for a person to approve or reject them. It is how "agents prepare, a human pays" is enforced.

### Relationships

- `tickets.invoice_id` → `invoices.id` (declared foreign key)
- `tickets.lease_id` → `leases.id` (declared foreign key)
- `invoices.vendor_id` → `vendors.id` (declared foreign key)
- `tickets.sku` / `tickets.size` → `inventory` (`sku`, `size`) and `tickets.sku` → `pricing.sku`. These are joins by value only; the schema doesn't declare these foreign keys.
- `payments.ref_id` points to an invoice or a lease, depending on `payments.kind`. The schema doesn't enforce this.
- `payments.account` → `cash_accounts.name`. This is also a join by value only.
- `payment_requests.ticket_id` → `tickets.id`, `payment_requests.payment_id` → `payments.id` (set on approval). Both are joins by value only.

### The three open tickets

**#101 `customer_order`: Tauhid Zaman, Classic Bulldog Tee (`CC-TEE-WHITE`), size S, qty 1**
- Inventory: size S is **out of stock** (qty 0, Aisle B). Sizes M/L/XL have 5/3/2 in stock.
- `invoice_id` 501: Bulldog Print Co (vendor 1, 5-day lead time) is doing an $840 **rush reprint of exactly this SKU and size**. The invoice is still `open` and was due **2026-08-28**, so it is 3 days overdue.
- Pricing: the tee lists at $28 and costs $8.
- What this means: the customer can't get the shirt until the reprint arrives, and the overdue vendor bill may be holding up that reprint.

**#102 `rent_notice`: Elm City Properties, "Rent due"**
- `lease_id` 1: Chapel Street shop, $2,400/month, next due **2026-09-02**. That is 2 days after `date_today`, which matches the email.
- Cash: checking has $3,400 (as of 2026-08-31). The payments table is empty, so rent has not been paid yet.
- What this means: paying rent ($2,400) and invoice 501 ($840) together comes to $3,240, which leaves $160 in checking. Any payment should be added to `payments` with an `approved_by` value.

**#103 `price_override`: Yale AI Club, 20 × Basic Hoodie Big Yale (`CC-HOOD-NAVY`), size M, asking for a bulk discount**
- Inventory: there are only **8 size M** hoodies in stock (Aisle A). Across all sizes there are 32 (S 4, M 8, L 14, XL 6).
- Pricing: list price $58 and cost $22. That means 20 hoodies cost $1,160 at list price, $440 at cost, and the shop's maximum margin is $720.
- There is no linked invoice or lease. To fill the order, the shop would need to restock 12 more size M hoodies. Bulldog Print Co (apparel, 5-day lead time) is the likely vendor.
- What this means: any discount has to stay above the $22 cost. The club also needs to hear either that only 8 are available now or how long a restock will take.

## Ticket statuses

| Status | Meaning | Who sets it |
| --- | --- | --- |
| `open` | Not worked yet | Starting data, or a reset |
| `in_progress` | Work started but blocked for another stated reason | Boss |
| `awaiting_human_input` | The crew is done, and a person must act: approve a payment, send a drafted reply, place a restock order, or approve a larger discount | Boss (whenever its `needs_human` list isn't empty) |
| `waiting_on_customer` | The shop has replied and the customer must answer | A person, after actually sending the reply |
| `resolved` | Nothing is left for anyone | A person: approve with "Also close the ticket", or **Human steps done ✓** |

## Agent team (Problem 5)

The team is five PydanticAI agents in [`../backend/`](../backend/). Each has its own prompt file in [`../backend/prompts/`](../backend/prompts/), and all of them use **`gpt-6-luna` through Portkey** (`PORTKEY_API_KEY` from the repo root `.env`), called via the OpenAI Responses API. Shared wiring lives in [`../backend/team.py`](../backend/team.py), and the data types are in [`../backend/models.py`](../backend/models.py).

| Agent | File / prompt | Job | MCP tools it may call | Output |
| --- | --- | --- | --- | --- |
| **Boss** | [`boss.py`](../backend/boss.py) / [`boss.md`](../backend/prompts/boss.md) | Reads the ticket, routes work by ticket type, combines reports, and records the final status. Does no specialist work. | `get_ticket`, `list_open_tickets`, `get_shop_date`, `update_ticket` | `TicketOutcome` |
| **Inventory** | [`inventory.py`](../backend/inventory.py) / [`inventory.md`](../backend/prompts/inventory.md) | Stock for the exact SKU/size, in-stock alternatives, shortfalls, restock vendor, lead time, and a pending reprint linked by invoice. Can't change stock or place orders. | `get_ticket`, `get_shop_date`, `get_stock_for_sku_and_size`, `list_vendors`, `get_invoice_and_vendor` | `AgentReport` |
| **Accounting** | [`accounting.py`](../backend/accounting.py) / [`accounting.md`](../backend/prompts/accounting.md) | Prices, the discount policy, cash, and vendor invoices. The **only** agent that can *prepare* a payment request; it can never pay. | `get_ticket`, `get_shop_date`, `get_unit_cost_and_list_price`, `quote_price_for_quantity`, `get_rent_due_and_cash_balance`, `get_cash_balance`, `list_leases`, `get_invoice_and_vendor`, `list_payments`, `request_payment_approval`, `list_payment_requests` | `AgentReport` |
| **Facilities** | [`facilities.py`](../backend/facilities.py) / [`facilities.md`](../backend/prompts/facilities.md) | The lease and landlord. Checks rent notices against the lease (fraud check) before anyone pays. Can't pay. | `get_ticket`, `get_shop_date`, `get_rent_due_and_cash_balance`, `list_payments` | `AgentReport` |
| **Customer Service** | [`customer_service.py`](../backend/customer_service.py) / [`customer_service.md`](../backend/prompts/customer_service.md) | Drafts replies to requesters from confirmed facts only. Never sends them, and never shares costs, margins, cash, or vendor details. | `get_ticket`, `get_shop_date`, `get_stock_for_sku_and_size` | `AgentReport` |

**Delegation (full connectivity).** Every agent has a `delegate(teammate, task)` tool and can hand work to any of the other four. The delegated run returns its structured report as the tool result. Limits:
- An agent can't delegate to itself or to any agent already in the current chain, which prevents ping-pong loops.
- The chain can be at most 2 hops deep (Boss → specialist → specialist).
- Each ticket gets at most 5 delegations.
- A refused delegation comes back to the model as `{"refused": reason}` and is audited.

**Agent loop.** `team.run_agent` drives each agent with `Agent.iter`. Each loop goes user prompt → model request → model response (tool calls) → tool results → … → end. Every node is written to the audit trail as it happens.

**Entry points.** Both go through `team.run_ticket`.
- **Dashboard API:** from `backend/`, with the HW 5 venv active, run `uvicorn main:app --reload --port 8000`. Then call `POST /tickets/{id}/run` (routes are listed below).
- **Command line:** from the `HW 5` folder, run `.venv/bin/python backend/run.py` to handle every open ticket, or add `--ticket 102` to handle one. `--db` and `--audit` point at other files, for example a scratch copy for tests.

No entry point lets an agent pay. Accounting files a payment request, and a person approves it through the API.

### Backend routes (Problem 7, [`../backend/main.py`](../backend/main.py))

Every route reads or writes shop data through the same `campus-customs` MCP connection the agents use. `main.py` contains no SQL. CORS allows the Vite page `http://localhost:5173` (plus other localhost ports, in case Vite moves), set by `FRONTEND_ORIGINS`.

- `GET /health`: liveness check; shows which DB file and model the server is using.
- `GET /tickets`: all 3 tickets with their DB status, a board `state` (`open`, `running`, `awaiting_human`, `waiting_on_customer`, or `resolved`), and a `pending_approvals` count.
- `POST /tickets/{id}/run`: starts the agent team (the Boss) on that ticket in the background and returns a `run_id` right away (409 if agents are already working on it).
- `GET /tickets/{id}/summary`: what each agent did on the ticket's latest run (its own summary, tools used, hand-offs, customer draft, items for a human), read from the audit trail.
- `GET /runs/{run_id}`: whether a dashboard run is `running`, `done` (with the Boss's `TicketOutcome`), or `error`.
- `GET /events?after=N&ticket_id=&run_id=&limit=`: recent audit events, showing what each agent said and which tools it used. `next_after` lets the board fetch only the new events.
- `GET /approvals?status=pending`: payment requests the agents prepared and that are waiting for a person.
- `POST /approvals/{id}/approve`: after a person clicks approve, pays the request (the **only route that changes cash**), adds a signed note to the ticket, and can mark it resolved (`resolve_ticket`). Otherwise a customer ticket with nothing left pending moves to `waiting_on_customer`.
- `POST /tickets/{id}/close`: a person confirms they finished the human steps (sent the reply, and so on), so the ticket becomes `resolved`. It returns 409 while agents run, before the crew has worked the ticket, or while a payment is pending, and adds a signed note.
- `POST /approvals/{id}/reject`: a person rejects the request; no money moves.
- `GET /cash`: the current checking balance from `cash_accounts`.
- `POST /reset`: restores `campus_customs_new.db` from the original `campus_customs.db` for a fresh run (409 while agents are running). The audit trail is kept, and the reset is recorded in it.

### Data types ([`models.py`](../backend/models.py))

- **`AgentReport`**: a specialist's answer. Fields: `summary`; `facts_used` (each fact paired with the tool or teammate it came from, so claims can be traced); `actions_taken` (writes that actually happened, with ids); `recommendations`; `needs_human` (approvals or actions left for a person); and `customer_message` (Customer Service's draft only).
- **`TicketOutcome`**: the Boss's final decision. Fields: `final_status`, which matches what it wrote with `update_ticket`; `decision`; actions; `delegated_to`; the customer draft; `needs_human`; and `facts_used`.
- **`FactUsed`**: a `source` plus a `fact`.
- **`ShopDeps`**: per-run context. Fields: `run_id`, `ticket_id`, the delegation `chain`, the audit path, the shared `TeamBudget`, and the current loop `step`.
- **`TeamBudget`**: the delegation caps shared across one ticket.
- **`AuditEntry`**: one line of the audit trail (below).

### Audit trail: `output/audit_trail.json`

[`audit.py`](../backend/audit.py) appends to a JSON array **as each event happens**. It inserts new entries before the closing `]` under a file lock, so earlier runs are never rewritten or wiped. Every entry records:
- `time`, `run_id`, and `ticket_id`;
- `agent`, `agent_run_id`, `parent`, and `depth`, which show where the agent sits in the delegation chain;
- the loop `step`, the `event`, and `detail`.

| Event | Recorded detail |
| --- | --- |
| `ticket_start` / `ticket_error` | DB path, model / error |
| `payment_approved`, `payment_rejected`, `ticket_closed`, `db_reset` (agent = `human`) | The person who acted, the request id, and the tool result |
| `agent_start` / `agent_end` / `agent_error` | Task given, prompt file, model / full typed output and the team's token and request usage so far |
| `loop_user_prompt`, `loop_model_request`, `loop_model_response`, `loop_end` | What went to the model (tool returns, retries) and what came back (text, tool calls with arguments, finish reason, tokens) |
| `mcp_tool_call` / `mcp_tool_blocked` / `mcp_tool_error` | Tool, arguments (including harness-filled `approved_by`/`author`), result, and latency, or the reason it was blocked |
| `delegation` / `delegation_refused` | From → to, the full task, delegations used, or the refusal reason |

## Dashboard (Problem 8, [`../frontend/`](../frontend/))

"The Coral Desk" is a React + Vite + TypeScript board that runs with `npm run dev` on `http://localhost:5173` and calls the API at `VITE_API_URL` (default `http://localhost:8000`). The full design rationale is in [`design.md`](design.md).

| Board area | Shows / does | Routes |
| --- | --- | --- |
| Tide pool | The 3 tickets as clams: closed when open, glowing aqua while the crew dives, glowing gold with an **Awaiting human input** pill and a "needs you" badge when a person must act, and opened to a pearl only when resolved. | `GET /tickets` |
| Ticket card | Ticket facts and the signed note history. **Send the crew** starts the agents; **Human steps done ✓** (with the crew's to-do list shown in a confirmation) lets a person resolve the ticket after doing those steps. | `POST /tickets/{id}/run`, `POST /tickets/{id}/close` |
| The crew | Five SVG creatures (whale = Boss, octopus = Inventory, turtle = Accounting, hermit crab = Facilities, dolphin = Customer Service). Each shows live state (talking, waiting on a teammate, done, resting) and a plain-language speech bubble. | `GET /events` |
| Captain's log | The Boss's decision; per-agent summary, tools, and hand-offs; the customer draft as a postcard; a "For you" list. | `GET /tickets/{id}/summary` |
| Sonar feed | Every step, color-coded by agent, newest first | `GET /events?after=N` |
| Treasure chest | The checking balance. When money leaves, the chest shakes and sinks coins, and a −$ chip appears. | `GET /cash` |
| Messages in bottles | Pending payment requests, each showing the amount, reason, and what the balance would be after. **Approve & pay** / **Send back** require a signed name. | `GET /approvals`, `POST /approvals/{id}/approve`, `/reject` |
| Turn the tide | Reset the DB, after a confirmation | `POST /reset` |

## MCP tools

Every agent uses these tools from [`../mcp_server/server.py`](../mcp_server/server.py), a FastMCP server called `campus-customs` over stdio. Every value a tool returns comes from `data/campus_customs_new.db` (plus arithmetic on those values). A missing row comes back as `"found": false` with a message rather than a guess. The agents have **no other path to shop data**: the backend has no SQL, and all reads and writes go through the one MCP connection created in `team.connect_mcp`. `payment_requests` is the one table this project adds. The MCP server creates it on the first request, and `POST /reset` removes it again.

**Connection (Problem 4):** the server is registered as `campus-customs` in the project root `my-app/.mcp.json` for Claude Code. It uses the HW 5 `.venv` Python. The original three tools were smoke-tested through Claude Code, and all outputs matched the DB (see [`mcp_smoke.json`](mcp_smoke.json)). The agent backend launches the same server script over stdio.

### Tool list

| Tool | Tables | Kind | Ticket it unlocks |
| --- | --- | --- | --- |
| `get_shop_date` | `desk` | read | All three: due dates and estimates count from 2026-08-31 |
| `list_open_tickets` | `tickets` | read | The queue; `run.py` uses it to find 101/102/103 |
| `get_ticket` | `tickets` | read | All three: the starting point for every agent |
| `get_stock_for_sku_and_size` | `inventory` | read | **#101** (tee S = 0), **#103** (hoodie M = 8 of 20) |
| `list_vendors` | `vendors` | read | **#103** (who restocks hoodies, 5-day lead time), **#101** |
| `get_invoice_and_vendor` | `invoices`, `vendors`, `desk` | read | **#101** (invoice 501: $840 reprint, 3 days overdue) |
| `get_rent_due_and_cash_balance` | `leases`, `cash_accounts`, `desk` | read | **#102** (rent $2,400 due in 2 days; checking $3,400) |
| `list_leases` | `leases`, `desk` | read | **#101** (Accounting checks the rent reserve before preparing the invoice 501 payment; the ticket has no lease id) |
| `get_unit_cost_and_list_price` | `pricing` | read | **#103** (list $58, cost $22) |
| `quote_price_for_quantity` | `pricing` | read (computes) | **#103** (prices a discount and flags `below_cost`) |
| `list_payments` | `payments` | read | **#101/#102** (stops double payments) |
| `list_tickets` | `tickets` | read | All three: the dashboard's ticket list (every status) |
| `get_cash_balance` | `cash_accounts` | read | **#101/#102**: the dashboard's checking balance |
| `request_payment_approval` | writes `payment_requests`; reads `invoices`, `leases`, `payments`, `cash_accounts`, `desk` | **write** (no money) | **#102** (prepare rent), **#101** (prepare invoice 501) |
| `list_payment_requests` | `payment_requests` | read | **#101/#102** (avoid duplicates; the dashboard's approval list) |
| `approve_payment_request` | writes `payment_requests`, `payments`, `cash_accounts`, `invoices` | **write (moves money)**, human only | **#101/#102**, called only by `POST /approvals/{id}/approve` |
| `reject_payment_request` | writes `payment_requests` | **write**, human only | Called only by `POST /approvals/{id}/reject` |
| `update_ticket` | writes `tickets`; reads `desk` | **write** | All three: final status and a signed, dated note |

### Why the three Problem 3 tools fit their tickets

**`get_stock_for_sku_and_size(sku, size)`**
- **Reads:** `inventory`
- **Unlocks ticket:** **#101**, Tauhid Zaman's order for 1 Classic Bulldog Tee (`CC-TEE-WHITE`) in size S
- **Why it's the right tool:** #101 depends on whether a size S tee is on the shelf. This tool returns `qty` 0 for `CC-TEE-WHITE`/S, which shows the order can't be filled today. It also lists M/L/XL at 5/3/2, so the agent can offer a size that is in stock rather than inventing availability.

**`get_rent_due_and_cash_balance(lease_id)`**
- **Reads:** `leases`, `cash_accounts`, `desk`
- **Unlocks ticket:** **#102**, Elm City Properties' "Rent due" notice (`lease_id` 1)
- **Why it's the right tool:** #102 is a claim that "shop rent [is] due in 2 days." This tool checks that claim with one call: it returns $2,400 rent due 2026-09-02, the desk date of 2026-08-31 (so `days_until_due` is 2), and $3,400 in checking. That tells the agent the notice is real and the shop can cover it.

**`get_unit_cost_and_list_price(sku)`**
- **Reads:** `pricing`
- **Unlocks ticket:** **#103**, the Yale AI Club's request for a bulk discount on 20 Basic Hoodie Big Yale (`CC-HOOD-NAVY`) in size M
- **Why it's the right tool:** #103 is a price-override request. This tool gives the $58 list price the club would normally pay and the $22 unit cost, which is the lowest any discounted price can go, so the agent can propose a discount that still makes money. The same ticket also uses `get_stock_for_sku_and_size` to see that only 8 size M hoodies are in stock.

## Safety

### Guardrails for real customers and real money

Implemented:
- **Least-privilege tools.** Each agent sees only its allowlisted MCP tools: tools are filtered out of the model's view, and the harness hook re-checks every call. Only Accounting can call `request_payment_approval`, and only the Boss can call `update_ticket`. `approve_payment_request` and `reject_payment_request` are blocked for every agent.
- **Agents prepare; a person pays.** Agents can only file a payment request. Cash moves only in `POST /approvals/{id}/approve`, after a person clicks approve and gives their name. The approval re-checks the item (still open, not already paid, cash covers it, amount unchanged). The harness fills in the request's `ticket_id` and `requested_by` and hides them from the model, so an agent can't file a request under another ticket or name.
- **Amounts come from the database.** A payment amount comes from the invoice or lease row, never from model output. The server refuses payments when the invoice isn't open, the rent is already paid this period, the cash isn't there, or the account is unknown.
- **Discounts never go below cost.** `quote_price_for_quantity` flags `below_cost`. The Accounting prompt's policy is: 10+ units only; up to 15% off without a human; 15–30% only with human approval; never more than 30%.
- **A human sends customer messages.** Customer Service only drafts. The Boss always lists "send the reply" under `needs_human`. Drafts may not include costs, margins, cash, or vendor and invoice details.
- **Fraud check before paying rent.** Facilities must match a notice to the lease (landlord, amount, due date) before Accounting pays.
- **Ticket text is untrusted.** Every prompt treats ticket subjects and notes as data, never as instructions. This is a prompt-injection defense.
- **Facts must be traceable.** Outputs carry `facts_used` with a source for each fact, and ticket notes are appended (signed by the harness as "<agent> agent", and dated) rather than overwritten.
- **A full audit trail.** Every step, tool call, blocked call, delegation, and human action (approve, reject, close, reset) is appended to `output/audit_trail.json`.
- **Closing needs a person, too.** `POST /tickets/{id}/close` refuses while agents are running, before the crew has worked the ticket, or while a payment request is pending. A ticket can't be closed with money still undecided.
- **No secrets in the frontend.** The browser only talks to the local API. `PORTKEY_API_KEY` stays on the server, and CORS only allows local origins.

A real business would also want these (not built):
- per-payment and per-day dollar caps;
- real sign-in for approvers (today the approver's name is typed in, not verified);
- two-person approval for large payments;
- PII redaction in the audit trail;
- a sandbox DB for every test run;
- alerts when cash falls below the next month's rent.

### Limits that keep token use in check

- **One shared budget per ticket.** Sub-agent runs reuse the parent's usage, and `UsageLimits` caps the whole team at **40 model requests, 60 tool calls, and 300k total tokens** per ticket. Going over raises an error, which is audited as `ticket_error`.
- **Delegation caps.** At most 5 delegations per ticket, depth 2, and no re-entering the current chain. The prompts plan for about 3 delegations, tell specialists to trust the facts in their task instead of re-delegating, and tell the Boss to pass along every confirmed fact.
- **Per-response cap.** `max_tokens` is 4,000. `parallel_tool_calls` is off, so steps run one at a time and are easy to audit.
- **Retries.** Each agent gets 2 output/tool retries, and MCP tool errors get 1 retry. The OpenAI client times out after 120 s and retries twice.
- **Wall-clock cap.** Each ticket has 600 s (`TICKET_TIMEOUT_S` in `team.py`, used by both the CLI and the API), so a hung request fails cleanly instead of stalling the queue.
- **Small payloads.** Audit fields are trimmed to 400 characters (final outputs are kept whole). Tools return only the rows a ticket needs.
- **Measured on scratch copies of the DB.** After tightening the prompts, a full ticket took about 16–17 model requests and about 40k input tokens. Before the fix, ticket 103 used 39 requests and 92k input tokens.
- **Measured in the final run (Problem 9):**

  | Ticket | Model requests | Tool calls | Input tokens | Output tokens |
  | --- | --- | --- | --- | --- |
  | 101 | 22 | 18 | 58,539 | 4,099 |
  | 102 | 16 | 13 | 41,043 | 2,215 |
  | 103 | 17 | 13 | 40,862 | 3,495 |
  | **Total** | **55** | **44** | **140,444** | **9,809** |

  All three stayed well under the 40-request / 300k-token cap.

## Final run (Problem 9, re-run cleanly before submission)

The database was reset on the board ("Turn the tide", 2026-10-13 22:06 UTC), and tickets 101, 102, and 103 were then run one at a time from the board on `data/campus_customs_new.db` (runs `305e693a49ea`, `467a5f1bffe0`, `aba903a1d23a`). Earlier rehearsal runs stay in the append-only trail above them. Every step was appended to [`audit_trail.json`](audit_trail.json). Full detail is in [`resolved_tickets.json`](resolved_tickets.json), the plan-vs-actual and Cash tabs of [`desk_tickets.html`](desk_tickets.html), and the screenshots in [`resolved_board.html`](resolved_board.html).

| Ticket | Delegations (actual) | Money | Human actions | Final status |
| --- | --- | --- | --- | --- |
| 101 | Boss → Inventory, Accounting, Customer Service | Request #1, invoice 501: **−$840.00** | Approved #1. The reply to Tauhid still needs to be sent. | awaiting_human_input |
| 102 | Boss → Facilities, Accounting | Request #2, lease 1 rent: **−$2,400.00** | Approved #2 with "Also close the ticket" (the last step left) | resolved |
| 103 | Boss → Inventory, Accounting, Customer Service | none (a quote: 8 × $58.00 = $464.00) | None yet. The offer still needs to be sent, and the 12-unit restock decided. | awaiting_human_input |

**Cash:** $3,400.00 − $840.00 − $2,400.00 − $0.00 = **$160.00**, which equals `cash_accounts.checking`. Both approvals were signed "Claude (for Robert Daly)", because the board was operated by Claude at the user's request. 101 and 103 were deliberately left at `awaiting_human_input`: marking them resolved would claim replies were sent when they weren't.
