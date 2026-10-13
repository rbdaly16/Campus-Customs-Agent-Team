"""Run the Campus Customs agent team on open tickets from the command line. The Boss handles
each ticket and delegates. (The dashboard does the same through backend/main.py.)

From the HW 5 folder:
  .venv/bin/python backend/run.py                 # every open ticket
  .venv/bin/python backend/run.py --ticket 102    # one ticket (repeatable)

Agents never move money: Accounting files payment requests, and a person approves them through
the API (POST /approvals/{id}/approve). Every step is appended to output/audit_trail.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path

import accounting, boss, customer_service, facilities, inventory  # noqa: F401  (registers the agents)
import audit
import team


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ticket", type=int, action="append", help="ticket id (repeatable); default: all open")
    parser.add_argument("--db", type=Path, default=team.DEFAULT_DB)
    parser.add_argument("--audit", type=Path, default=audit.DEFAULT_PATH)
    args = parser.parse_args()

    run_id = uuid.uuid4().hex[:12]
    mcp = team.connect_mcp(args.db.resolve())
    async with mcp:
        ids = args.ticket or [t["id"] for t in (await mcp.direct_call_tool("list_open_tickets", {}))["tickets"]]
        for ticket_id in ids:
            try:
                outcome = await team.run_ticket(ticket_id, run_id, args.audit.resolve())
            except Exception as e:
                print(f"Ticket {ticket_id} failed: {type(e).__name__}: {e}")
                continue
            print(json.dumps(outcome.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
