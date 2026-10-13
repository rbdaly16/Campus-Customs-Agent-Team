"""Campus Customs MCP server (FastMCP) over data/campus_customs_new.db.

Every agent in HW 5 gets its shop data through these tools; there is no other path to the
database. Each tool returns only values read from the database (plus arithmetic on them);
when a row is missing it says so instead of guessing. Write tools take amounts and dates
from the database, never from the caller. Agents can only *request* a payment; cash moves only
in approve_payment_request, which the dashboard API calls after a human clicks approve.

Set CAMPUS_CUSTOMS_DB to point at a different copy (e.g. a scratch DB for tests).

Run (stdio):  python server.py
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("CAMPUS_CUSTOMS_DB", HERE.parent / "data" / "campus_customs_new.db"))

# awaiting_human_input: a person at the shop must act (approve a payment, send a drafted reply, ...).
# waiting_on_customer: the shop has replied and the customer must answer. resolved: nothing left for anyone.
TICKET_STATUSES = ("open", "in_progress", "awaiting_human_input", "waiting_on_customer", "resolved")
PAYMENT_KINDS = ("invoice", "rent")

mcp = FastMCP("campus-customs")


def _connect(write: bool = False) -> sqlite3.Connection:
    """Open the working database (read-only unless `write`), rows addressable by column name."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode={'rw' if write else 'ro'}", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _shop_date(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT date_today FROM desk").fetchone()
    return row["date_today"] if row else None


def _days_between(start: str | None, end: str) -> int | None:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days if start else None


# ---------------------------------------------------------------- read tools


@mcp.tool
def get_shop_date() -> dict:
    """Return the shop's current date (`desk.date_today`) and any desk notes.

    All due dates, overdue checks, and delivery estimates must count from this date,
    not the real-world clock. Reads the `desk` table.
    """
    with _connect() as conn:
        row = conn.execute("SELECT date_today, notes FROM desk").fetchone()
    if row is None:
        return {"found": False, "message": "The desk table has no row."}
    return {"found": True, **dict(row)}


@mcp.tool
def list_open_tickets() -> dict:
    """List every ticket whose status is not `resolved`, oldest first. Reads the `tickets` table."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status != 'resolved' ORDER BY created_at, id"
        ).fetchall()
    return {"count": len(rows), "tickets": [dict(r) for r in rows]}


@mcp.tool
def list_tickets() -> dict:
    """List every ticket with its status (open, in progress, waiting, or resolved), oldest first.
    Reads the `tickets` table."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY created_at, id").fetchall()
    return {"count": len(rows), "tickets": [dict(r) for r in rows]}


@mcp.tool
def get_cash_balance(account: str = "checking") -> dict:
    """Return one cash account's balance and as-of date. Reads `cash_accounts`."""
    with _connect() as conn:
        row = conn.execute("SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account,)).fetchone()
    if row is None:
        return {"found": False, "message": f"No cash account named {account!r}."}
    return {"found": True, **dict(row)}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Return one ticket with all its fields (type, requester, SKU/size/qty, linked lease or
    invoice, status, notes). Reads the `tickets` table."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        return {"found": False, "message": f"No ticket with id {ticket_id}."}
    return {"found": True, "ticket": dict(row)}


@mcp.tool
def get_stock_for_sku_and_size(sku: str, size: str) -> dict:
    """Return how many units of one SKU in one size are on the shelf, and where.

    Also lists every other size of the same SKU so an agent can offer an in-stock
    alternative. Reads the `inventory` table.
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? ORDER BY rowid",
            (sku,),
        ).fetchall()
    if not rows:
        return {"found": False, "message": f"No inventory rows for SKU {sku!r}."}
    requested = next((dict(r) for r in rows if r["size"] == size), None)
    return {
        "found": requested is not None,
        "requested": requested,
        "message": None if requested else f"SKU {sku!r} has no size {size!r} in inventory.",
        "all_sizes": [dict(r) for r in rows],
    }


@mcp.tool
def list_vendors() -> dict:
    """List every vendor with its specialty and lead time in days, so an agent can pick who
    restocks an item and estimate when it arrives. Reads the `vendors` table."""
    with _connect() as conn:
        rows = conn.execute("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id").fetchall()
    return {"count": len(rows), "vendors": [dict(r) for r in rows]}


@mcp.tool
def get_invoice_and_vendor(invoice_id: int) -> dict:
    """Return one vendor invoice, the vendor it is owed to, and how many days overdue it is.

    `days_overdue` is `desk.date_today` minus `due_date` (negative means not yet due).
    Reads `invoices`, `vendors`, and `desk`.
    """
    with _connect() as conn:
        inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if inv is None:
            return {"found": False, "message": f"No invoice with id {invoice_id}."}
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (inv["vendor_id"],)).fetchone()
        today = _shop_date(conn)
    return {
        "found": True,
        "invoice": dict(inv),
        "vendor": dict(vendor) if vendor else None,
        "date_today": today,
        "days_overdue": _days_between(inv["due_date"], today) if today else None,
    }


@mcp.tool
def get_rent_due_and_cash_balance(lease_id: int) -> dict:
    """Return a lease's rent amount and due date next to the shop's cash balances.

    `date_today` comes from the `desk` table (the shop's current date), and
    `days_until_due` is next_due minus date_today. Reads `leases`, `cash_accounts`,
    and `desk`.
    """
    with _connect() as conn:
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        accounts = conn.execute("SELECT name, balance, date FROM cash_accounts").fetchall()
        date_today = _shop_date(conn)
    if lease is None:
        return {"found": False, "message": f"No lease with id {lease_id}."}
    return {
        "found": True,
        "lease": dict(lease),
        "date_today": date_today,
        "days_until_due": _days_between(date_today, lease["next_due"]),
        "cash_accounts": [dict(a) for a in accounts],
    }


@mcp.tool
def list_leases() -> dict:
    """List every lease with its rent, next due date, and days until due (from the shop date),
    so an agent can check upcoming rent without a lease id. Reads `leases` and `desk`."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM leases ORDER BY next_due").fetchall()
        today = _shop_date(conn)
    return {
        "date_today": today,
        "leases": [{**dict(r), "days_until_due": _days_between(today, r["next_due"])} for r in rows],
    }


@mcp.tool
def get_unit_cost_and_list_price(sku: str) -> dict:
    """Return one SKU's unit cost (the floor for any discount) and its list price.

    Reads the `pricing` table.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
    if row is None:
        return {"found": False, "message": f"No pricing row for SKU {sku!r}."}
    return {"found": True, **dict(row)}


@mcp.tool
def quote_price_for_quantity(sku: str, qty: int, discount_percent: float = 0.0) -> dict:
    """Price `qty` units of a SKU at `discount_percent` off list, and check it against cost.

    Returns per-unit and total figures plus `below_cost`, which is true when the discounted
    unit price would be under `unit_cost`. Reads the `pricing` table. Does not save anything.
    """
    if qty <= 0 or not 0 <= discount_percent < 100:
        return {"found": False, "message": "qty must be positive and discount_percent between 0 and 100."}
    with _connect() as conn:
        row = conn.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if row is None:
        return {"found": False, "message": f"No pricing row for SKU {sku!r}."}
    unit_price = round(row["list_price"] * (1 - discount_percent / 100), 2)
    return {
        "found": True,
        "sku": sku,
        "qty": qty,
        "list_price": row["list_price"],
        "unit_cost": row["unit_cost"],
        "discount_percent": discount_percent,
        "unit_price": unit_price,
        "total_at_list": round(row["list_price"] * qty, 2),
        "total_quoted": round(unit_price * qty, 2),
        "total_cost": round(row["unit_cost"] * qty, 2),
        "margin_total": round((unit_price - row["unit_cost"]) * qty, 2),
        "below_cost": unit_price < row["unit_cost"],
    }


@mcp.tool
def list_payments(kind: str | None = None, ref_id: int | None = None) -> dict:
    """List recorded payments, optionally only one `kind` ('invoice' or 'rent') and/or one
    `ref_id`, so an agent can check whether something is already paid. Reads `payments`."""
    sql, params = "SELECT * FROM payments WHERE 1=1", []
    if kind is not None:
        sql, params = sql + " AND kind = ?", [*params, kind]
    if ref_id is not None:
        sql, params = sql + " AND ref_id = ?", [*params, ref_id]
    with _connect() as conn:
        rows = conn.execute(sql + " ORDER BY id", params).fetchall()
    return {"count": len(rows), "payments": [dict(r) for r in rows]}


# ---------------------------------------------------------------- write tools


REQUESTS_DDL = """
CREATE TABLE IF NOT EXISTS payment_requests (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    kind TEXT NOT NULL,
    ref_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    account TEXT NOT NULL,
    reason TEXT,
    requested_by TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    decided_by TEXT,
    decided_at TEXT,
    decision_note TEXT,
    payment_id INTEGER
)"""


def _has_requests_table(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='payment_requests'").fetchone() is not None


def _payable_amount(conn: sqlite3.Connection, kind: str, ref_id: int, account: str) -> tuple[float | None, str | None]:
    """Amount owed for an invoice or this period's rent, from the DB, or the reason it can't be paid."""
    if kind not in PAYMENT_KINDS:
        return None, f"kind must be one of {PAYMENT_KINDS}."
    if kind == "invoice":
        inv = conn.execute("SELECT amount, status FROM invoices WHERE id = ?", (ref_id,)).fetchone()
        if inv is None:
            return None, f"No invoice with id {ref_id}."
        if inv["status"] != "open":
            return None, f"Invoice {ref_id} is {inv['status']!r}, not open."
        amount = inv["amount"]
    else:
        lease = conn.execute("SELECT monthly_rent, next_due FROM leases WHERE id = ?", (ref_id,)).fetchone()
        if lease is None:
            return None, f"No lease with id {ref_id}."
        period_start = (date.fromisoformat(lease["next_due"]) - timedelta(days=31)).isoformat()
        dup = conn.execute(
            "SELECT id FROM payments WHERE kind = 'rent' AND ref_id = ? AND paid_at > ?", (ref_id, period_start)
        ).fetchone()
        if dup:
            return None, f"Rent due {lease['next_due']} is already paid (payment {dup['id']})."
        amount = lease["monthly_rent"]
    acct = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
    if acct is None:
        return None, f"No cash account named {account!r}."
    if acct["balance"] < amount:
        return None, f"{account} has {acct['balance']:.2f}, short of {amount:.2f}."
    return amount, None


@mcp.tool
def request_payment_approval(ticket_id: int, kind: str, ref_id: int, account: str, reason: str, requested_by: str) -> dict:
    """Prepare a payment for a human to approve. Moves no money.

    `kind`='invoice' (ref_id = invoice id) or 'rent' (ref_id = lease id). The amount comes from
    the database. Refuses if the item can't be paid right now (not open, already paid, cash
    short) or a request for it is already pending. Writes `payment_requests`; reads `invoices`,
    `leases`, `payments`, `cash_accounts`, `desk`.
    """
    if not requested_by.strip():
        return {"ok": False, "message": "requested_by is required."}
    with _connect(write=True) as conn:
        conn.execute(REQUESTS_DDL)
        amount, error = _payable_amount(conn, kind, ref_id, account)
        if error:
            return {"ok": False, "message": error}
        dup = conn.execute(
            "SELECT id FROM payment_requests WHERE kind = ? AND ref_id = ? AND status = 'pending'", (kind, ref_id)
        ).fetchone()
        if dup:
            return {"ok": False, "message": f"Payment request {dup['id']} for this {kind} is already pending."}
        cur = conn.execute(
            "INSERT INTO payment_requests (ticket_id, kind, ref_id, amount, account, reason, requested_by, requested_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, kind, ref_id, amount, account, reason.strip(), requested_by.strip(), _shop_date(conn)),
        )
        row = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (cur.lastrowid,)).fetchone()
    return {"ok": True, "request": dict(row), "message": "Pending human approval; no money has moved."}


@mcp.tool
def list_payment_requests(status: str | None = None, ticket_id: int | None = None) -> dict:
    """List payment requests, optionally only one `status` ('pending', 'approved', 'rejected')
    and/or one ticket. Reads `payment_requests`."""
    with _connect() as conn:
        if not _has_requests_table(conn):
            return {"count": 0, "requests": []}
        sql, params = "SELECT * FROM payment_requests WHERE 1=1", []
        if status is not None:
            sql, params = sql + " AND status = ?", [*params, status]
        if ticket_id is not None:
            sql, params = sql + " AND ticket_id = ?", [*params, ticket_id]
        rows = conn.execute(sql + " ORDER BY id", params).fetchall()
    return {"count": len(rows), "requests": [dict(r) for r in rows]}


@mcp.tool
def approve_payment_request(request_id: int, approved_by: str, note: str = "") -> dict:
    """Pay a pending request after a human approves it. This is the only tool that moves cash.

    Re-checks the item against the database first (still open, not already paid, cash covers
    it, amount unchanged). On success it adds a `payments` row dated `desk.date_today`, lowers
    the account balance, marks an invoice `paid`, and marks the request `approved`.
    Writes `payment_requests`, `payments`, `cash_accounts`, `invoices`.
    """
    if not approved_by.strip():
        return {"ok": False, "message": "approved_by is required: a human must approve every payment."}
    with _connect(write=True) as conn:
        if not _has_requests_table(conn):
            return {"ok": False, "message": f"No payment request with id {request_id}."}
        req = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            return {"ok": False, "message": f"No payment request with id {request_id}."}
        if req["status"] != "pending":
            return {"ok": False, "message": f"Request {request_id} is already {req['status']}."}
        amount, error = _payable_amount(conn, req["kind"], req["ref_id"], req["account"])
        if error:
            return {"ok": False, "message": error}
        if amount != req["amount"]:
            return {"ok": False, "message": f"Amount owed is now {amount:.2f}, not the requested {req['amount']:.2f}."}
        today = _shop_date(conn)
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (req["kind"], req["ref_id"], amount, req["account"], today, approved_by.strip()),
        )
        conn.execute(
            "UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = ?", (amount, today, req["account"])
        )
        if req["kind"] == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (req["ref_id"],))
        conn.execute(
            "UPDATE payment_requests SET status = 'approved', decided_by = ?, decided_at = ?, decision_note = ?,"
            " payment_id = ? WHERE id = ?",
            (approved_by.strip(), today, note.strip() or None, cur.lastrowid, request_id),
        )
        balance = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (req["account"],)).fetchone()[0]
    return {
        "ok": True,
        "request_id": request_id,
        "ticket_id": req["ticket_id"],
        "payment_id": cur.lastrowid,
        "kind": req["kind"],
        "ref_id": req["ref_id"],
        "amount": amount,
        "account": req["account"],
        "paid_at": today,
        "approved_by": approved_by.strip(),
        "balance_after": balance,
    }


@mcp.tool
def reject_payment_request(request_id: int, rejected_by: str, reason: str) -> dict:
    """Mark a pending payment request rejected. Moves no money. Writes `payment_requests`."""
    if not rejected_by.strip():
        return {"ok": False, "message": "rejected_by is required."}
    with _connect(write=True) as conn:
        if not _has_requests_table(conn):
            return {"ok": False, "message": f"No payment request with id {request_id}."}
        req = conn.execute("SELECT status, ticket_id FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            return {"ok": False, "message": f"No payment request with id {request_id}."}
        if req["status"] != "pending":
            return {"ok": False, "message": f"Request {request_id} is already {req['status']}."}
        conn.execute(
            "UPDATE payment_requests SET status = 'rejected', decided_by = ?, decided_at = ?, decision_note = ?"
            " WHERE id = ?",
            (rejected_by.strip(), _shop_date(conn), reason.strip() or None, request_id),
        )
    return {"ok": True, "request_id": request_id, "ticket_id": req["ticket_id"], "status": "rejected"}


@mcp.tool
def update_ticket(ticket_id: int, status: str, note: str, author: str) -> dict:
    """Set a ticket's status and append a dated, signed note. Earlier notes are kept.

    `status` must be one of: open, in_progress, awaiting_human_input, waiting_on_customer,
    resolved. Writes the `tickets` table; reads `desk` for the note date.
    """
    if status not in TICKET_STATUSES:
        return {"ok": False, "message": f"status must be one of {TICKET_STATUSES}."}
    if not note.strip() or not author.strip():
        return {"ok": False, "message": "note and author are required."}
    with _connect(write=True) as conn:
        row = conn.execute("SELECT notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"ok": False, "message": f"No ticket with id {ticket_id}."}
        line = f"[{_shop_date(conn)} {author.strip()}] {note.strip()}"
        notes = f"{row['notes']}\n{line}" if row["notes"] else line
        conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, notes, ticket_id))
    return {"ok": True, "ticket_id": ticket_id, "status": status, "notes": notes}


if __name__ == "__main__":
    mcp.run(show_banner=False)
