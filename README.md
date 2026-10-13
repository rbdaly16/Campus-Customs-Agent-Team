# Campus Customs Agent Team: "The Coral Desk"

AI Foundations HW 5. This is a five-agent PydanticAI team that works the back-office tickets of **Campus Customs**, a Yale apparel shop. The agents are a Boss, Inventory, Accounting, Facilities, and Customer Service. Every shop fact comes from a FastMCP server over SQLite. A FastAPI backend serves an under-the-sea React dashboard where a person watches the crew work, approves payments, and closes tickets.

**Agents prepare; a person pays.** No agent can move money. Accounting only files a payment request, and cash changes only when a person clicks **Approve & pay** on the board.

## What's in the repo

| Path | What it is |
| --- | --- |
| `data/campus_customs.db` | The original database. It is never modified, and **Reset** copies from it. |
| `data/campus_customs_new.db` | The working copy, in its state at the end of the final run: checking **$160.00**, 102 resolved, 101 and 103 awaiting human input |
| `mcp_server/server.py` | FastMCP server with 18 tools: 14 read and 4 write. It is the only path to shop data. See [`mcp_server/README.md`](mcp_server/README.md). |
| `backend/` | PydanticAI agents: `boss.py`, `inventory.py`, `accounting.py`, `facilities.py`, `customer_service.py`. Also the prompts in `backend/prompts/`, data types in `models.py`, shared wiring and guardrails in `team.py`, the audit writer in `audit.py`, the CLI `run.py`, and the FastAPI app `main.py` |
| `frontend/` | React + Vite + TypeScript dashboard ("The Coral Desk") |
| `output/harness.md` | Manager-readable harness: tables, MCP tools, agents, API routes, dashboard, ticket statuses, safety rules, token limits, and the final run |
| `output/desk_tickets.html` | Opens on double-click. Tabs for 101/102/103 (Expected vs. Actual), **Cash** (an itemized ledger), and **Reflection** |
| `output/resolved_tickets.json` | Per ticket: final status, outcome, each agent's contribution, human approvals, and cash before and after |
| `output/resolved_board.html` | Opens on double-click. Screenshots of the board for each ticket in the final run |
| `output/audit_trail.json` | An append-only log of every agent-loop step, MCP call, hand-off, and human action |
| `output/design.md` | Dashboard design and rationale |
| `output/mcp_smoke.json` | MCP smoke test (Problem 4) |
| `AI_prompts.md` | Running log of the prompts used for each problem |

## Run it

Requirements: Python 3.11+, Node 20+, and a Portkey API key with access to `gpt-6-luna`.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then put your PORTKEY_API_KEY in .env
```

**Backend** (http://localhost:8000):

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

**Dashboard** (http://localhost:5173), in a second terminal:

```bash
cd frontend
cp .env.example .env          # VITE_API_URL=http://localhost:8000 (also the default)
npm install
npm run dev
```

On the board:
1. Sign your name in **Messages in bottles**.
2. Click **Turn the tide ↺** to reset `campus_customs_new.db` from the original.
3. Pick a ticket and click **Send the crew ↓**.
4. Approve the payments that wash up.
5. Click **Human steps done ✓** once you've actually done the remaining human steps (for example, sending the drafted reply).

**Command line** (no dashboard). This runs every open ticket; agents can only prepare payments:

```bash
.venv/bin/python backend/run.py
```

## Final run (summary)

| Ticket | Crew | Money | Final status |
| --- | --- | --- | --- |
| 101 Bulldog tee | Boss → Inventory, Accounting, Customer Service | −$840.00 (invoice 501, approved) | awaiting human input (the reply to Tauhid still has to be sent) |
| 102 Rent due | Boss → Facilities, Accounting | −$2,400.00 (lease 1 rent, approved) | resolved |
| 103 Hoodie discount | Boss → Inventory, Accounting, Customer Service | $0.00 (quote: 8 × $58.00 = $464.00) | awaiting human input (the offer still has to be sent) |

Checking: $3,400.00 − $840.00 − $2,400.00 = **$160.00**, which matches `cash_accounts` in `data/campus_customs_new.db`.

No `.env` file is committed. Copy `.env.example` and add your own key.
