# AI Prompts

This file records the prompts used while completing HW 5, along with what was missing after each first prompt and evidence of the work completed.

Future sections will use the following format:

## Problem [number]: [title]

### Prompt(s)

### What was missing after the first prompt

### Evidence

## Setup: Joke file

### Prompt(s)

HW5

yo! hw 5 /joke-file

### What was missing after the first prompt

No follow-up prompt was needed; the request named the target folder and the joke-file skill.

### Evidence

Created [`joke.txt`](joke.txt) with a short homework-themed joke.

## Problem 1: Vibe coder prompts

### Prompt(s)

nice! now Problem 1: Vibe coder prompts /homework-prompt-log

### What was missing after the first prompt

No follow-up prompt was needed; the request named the problem and the prompt-log skill.

### Evidence

Created this file, [`AI_prompts.md`](AI_prompts.md), using the same format as earlier homework logs.

## Problem 2: Study the Campus Customs database

### Prompt(s)

@"/Users/robertdaly/Downloads/data (3).zip"
Problem 2: Study the Campus Customs database

Open data/campus_customs.db and let's look through those tables and fields. 

Copy the original file to data/campus_customs_new.db 

Study the three open tickets so we see how they link to other tables

Then let's start output/harness.md /build-harness 
For each table, list the fields and one short line on why that table matters for the agents. We;ll keep growing this harness file in later problems

### What was missing after the first prompt

No follow-up prompt was needed; the request specified the zip, the database, the copy's filename, the tickets to study, and the harness format.

### Evidence

Unzipped the database into [`data/`](data/), copied it to [`data/campus_customs_new.db`](data/campus_customs_new.db) (byte-identical to the original), studied all 9 tables and the 3 open tickets, and started [`output/harness.md`](output/harness.md) with each table's fields, why it matters, the relationships between tables, and how each ticket links to other tables.

## Problem 3: Build the MCP server

### Prompt(s)

Problem 3: Build the MCP server

Write an MCP server in mcp_server/ using FastMCP. It will talk to data/campus_customs_new.db. You do not need to connect or run it in this problem though, we can do that later.

Also, every agent in this hw uses the tools in this MCP server. We're gonna add more tools to it latere. For now let's write 3 tools we'll need for the tickets in the database. and let's keep the names crystal clear. Never invent any data, only use info in the database.

In output/harness.md, list each of your 3 MCP tools. For every tool include: which table it reads, which ticket it helps unlock (101, 102, or 103) and 1 sentence on why that tool is the right one for that ticket. Let's be clear. Vague lines like "reds inventory" score low -- tie the tool to the ticket

Add a short mcp_server/README.md file that explains what the MCP server is for, which database file it uses, and the three tools it has

### What was missing after the first prompt

No follow-up prompt was needed; the request specified the folder, framework, database, number of tools, the no-invented-data rule, and what the harness and README must contain.

### Evidence

Wrote [`mcp_server/server.py`](mcp_server/server.py), a FastMCP server with three read-only tools: `get_stock_for_sku_and_size` (#101), `get_rent_due_and_cash_balance` (#102), and `get_unit_cost_and_list_price` (#103). Added [`mcp_server/README.md`](mcp_server/README.md) and a "MCP tools" section to [`output/harness.md`](output/harness.md). Created the HW 5 `.venv` and [`requirements.txt`](requirements.txt). Called each tool directly against the database (results matched the database, and missing rows returned `found: false`); the database file was unchanged afterward.

## Problem 4: Add the MCP server to vibe coder and test each tool

### Prompt(s)

Problem 4: Add the MCP server to vibe coder and test each tool

Let's add the MCP server to this project so we can call the tools. Save the connection JSON text in .mcp.json at the project root or whever you thiink it's best to save the local MCP server lists.

Then let's test each of the three MCP tools. Save the evidence in output/mcp_smoke.json

For every tool let's include:

* prompt you asked the vibe coder
* * the tool name
* * the tool output (must match values in data/campus_customs_new.db)


Sound goooooood!?

### What was missing after the first prompt

No follow-up prompt was needed; the request named the config file, the evidence file, and the three fields each test must include.

### Evidence

Added the `campus-customs` entry to the project root `.mcp.json` (`my-app/.mcp.json`, next to the existing local MCP servers). Because a running session only loads `.mcp.json` at startup, each tool was tested by sending a ticket prompt to a fresh headless Claude Code session (`claude -p`) with only the campus-customs server connected. All three tools were called through MCP, and their outputs matched rows read directly from the database. Results are in [`output/mcp_smoke.json`](output/mcp_smoke.json) (`all_match_database: true`). Also updated [`mcp_server/README.md`](mcp_server/README.md) and [`output/harness.md`](output/harness.md) with the connection.

## Problem 5: Build the agent team and grow the MCP tools

### Prompt(s)

Problem 5: Build the agent team and grow the MCP tools

Build the agentic team for Campus Customs using PydanticAI: Boss, Inventory, Accounting, Facilities, and Customer Service. Include prompts, models, and agent loops so they can delegate work to each other with full connectivity.

Put the agent prompts in backend/prompts/ and do one file per agent. Put data types in backend/models.py, and the agent files under backend/

Let's use the PORTKEY_API_KEY and ONLY gpt-6-luna for every agent.

Write each prompt in your own words with the shop rules that agent needs. More detailed prompts that cover all aspects of an agent's work and scope score higher than a short generic prompt

Let's add any tools the agents need to the MCP server so they can work on the open tickets. Shop facts come from the MCP server over data/campus_customs_new.db -- make sure you don't invent a second shop-tools layer that bypasses MCP

Wire the agents so they append to output/audit_trail.json as they run: for each agent-loop step, record enough to audit later. Append to this file and do not wipe it each run.

In output/harness.md, list each agent and each MCP tool (including ones you add in this problem) along with whcih table the tool uses. Also add a short safety section: the guardrails a real business would want when agents touh real customers and real money, plus limits that keep token use in check.

Update mcp_server/README.md so the tool list matches what you have now

### What was missing after the first prompt

No follow-up prompt was needed. Testing turned up two fixes made without a new prompt. First, the Portkey/Azure `gpt-6-luna` deployment rejects function tools with reasoning on `/chat/completions`, so the agents use the OpenAI Responses API. Second, the first test runs re-delegated for facts the agents already had (ticket 103 used 39 of 40 requests), so the prompts were tightened and the delegation cap was lowered.

### Evidence

- **Agents:** [`backend/boss.py`](backend/boss.py), [`inventory.py`](backend/inventory.py), [`accounting.py`](backend/accounting.py), [`facilities.py`](backend/facilities.py), [`customer_service.py`](backend/customer_service.py), with shared wiring in [`backend/team.py`](backend/team.py).
- **Prompts:** one per agent in [`backend/prompts/`](backend/prompts/).
- **Data types:** [`backend/models.py`](backend/models.py).
- **Audit writer:** [`backend/audit.py`](backend/audit.py).
- **Entry point:** [`backend/run.py`](backend/run.py).
- **MCP server:** grew from 3 to 12 tools in [`mcp_server/server.py`](mcp_server/server.py), with [`mcp_server/README.md`](mcp_server/README.md) updated to match.
- **Harness:** [`output/harness.md`](output/harness.md) now lists every agent and tool with the tables it uses, plus the safety and token-limit sections.
- **Testing:** test runs used scratch copies of the database and a scratch audit file, so `data/campus_customs_new.db` is unchanged and `output/audit_trail.json` will start with the first real run.
  - Ticket 102 with a test approver: Boss → Facilities → Accounting, rent paid, ticket resolved.
  - Tickets 101 and 103 with no approver: no payments; 3 Boss delegations each, about 16–17 model requests per ticket.

## Problem 6: Plan the three tickets

### Prompt(s)

Problem 6: Plan the three tickets

Before you wire the backend, write down what you expect the team to do on each open ticket. Build output/desk_tickets.html -- this should be a page you can double click with one tab per ticket (101, 102, and 103)

Also add empty Cash and Reflection tabs for later problems (leave them blank or with a short "coming later" note for now)

On each ticket tab, fill an Expected section only (leave room for an Actual section you will fill after you run the agents)

For each ticket's Expected section, write in your own words:

* Who the Boss should call first, and why
* All the agent delegations you expect - not "Boss calls everyone"
* Which MCP tools you expect that run to use


Plans that send every specialist on every ticket score low. you will compare this plan to what actually happens when your agents resolve the 3 tickets

### What was missing after the first prompt

No follow-up prompt was needed. This prompt arrived while Problem 5 was still being built and tested, so the backend already existed. The plan is based on the team's design (the Boss routing rules, each agent's tool allowlist, and the DB facts). The agents haven't run on the real working database yet.

### Evidence

Created [`output/desk_tickets.html`](output/desk_tickets.html), a standalone page with tabs for 101, 102, 103, Cash, and Reflection.
- Each ticket tab has an Expected section: who the Boss calls first and why, a numbered delegation table, the specialists *not* called and why, the expected MCP tools for each agent, and the expected result. It also has an empty Actual section.
- Planned delegations: 3 for 101 (no Facilities), 2 for 102 (no Inventory or Customer Service), and 3 for 103 (no Facilities).
- Checked in the browser: all 5 tabs switch correctly, and there are no console errors.

## Problem 7: Backend routes

### Prompt(s)

alright sweet! Yes, that looks great!

Problem 7: Backend routes

Lets get that React frontend dashboard some edits b/c it needs a backend it can call. In backend/main.py, use FastAPI and add routes that do the following:

* Return 3 tickets and whether each is open or resolved
* Take ticket id and run your agent team on that ticket
* Return recent agent events -- what each agent said and which tools they used -- so the board can refresh
* Approve a payment or purchase after a human clicks approve (agents only prepare the pay; this route is what actually changes cash)
* Return the current checking balance from cash_accounts
* Reset the database to the og values when we want try a fresh run


From the backend/ folder, start the server with:
uvicorn main:app --reload --port 8000

This turns on your backend at http://localhost:8000 so the frontend dashboard can call those routes. 

In output/harness.md, list each route in one line (what URL/what it does)

### What was missing after the first prompt

No follow-up prompt was needed. "Agents only prepare the pay" changed the Problem 5 design, where Accounting could pay when a run had an `--approver`. Accounting now only files a payment request, and the approve route is the only place cash changes. The prompt also didn't say how the board finds what to approve, so `GET /approvals` (and a reject route) were added. Only payments for invoices and rent are approvable; a new restock *purchase* isn't modeled, because the database has no purchase-order table.

### Evidence

- **Routes:** wrote [`backend/main.py`](backend/main.py): tickets, run, run status, events, approvals (list, approve, reject), cash, reset, and health. They reach the data through the same MCP connection the agents use; `main.py` has no SQL.
- **MCP server:** [`mcp_server/server.py`](mcp_server/server.py) dropped `record_payment` and added `list_tickets`, `get_cash_balance`, `request_payment_approval`, `list_payment_requests`, `approve_payment_request`, and `reject_payment_request`.
- **Harness and prompts:** [`backend/team.py`](backend/team.py) blocks every agent from the approve and reject tools and adds a shared `run_ticket` entry point. [`backend/run.py`](backend/run.py) no longer has `--approver`. Updated [`backend/prompts/accounting.md`](backend/prompts/accounting.md), [`boss.md`](backend/prompts/boss.md), and [`facilities.md`](backend/prompts/facilities.md).
- **Docs:** [`output/harness.md`](output/harness.md) has one line per route plus the updated tools and safety sections, and [`mcp_server/README.md`](mcp_server/README.md) is updated too. The payment lines in [`output/desk_tickets.html`](output/desk_tickets.html) now describe the prepare-then-approve flow.
- **Testing:** tested with the given `uvicorn main:app --reload --port 8000` command against a scratch DB and a scratch audit file.
  - Running ticket 102 led to Facilities, then Accounting, which filed request #1 ($2,400) while checking stayed at $3,400.
  - Approving the request paid it, checking went to $1,000, and the ticket was resolved.
  - A second approval, an unknown id, and an empty approver were each refused.
  - Running the same ticket twice, or resetting while agents were running, returned 409.
  - Reset restored the DB byte for byte and kept the audit trail.
- **Real paths:** the same command started on the real paths for read-only checks; the working DB is unchanged.

## Problem 8: Agent dashboard

### Prompt(s)

Problem 8: Agent dashboard

Build the frontend dashboard in frontend/ with React + Vite + TypeScript. The page should call the routes you built in Problem 7. At minimum the board should:

* List all three tickets
* Let you pick one ticket and start the agent team on it
* Show each agent and what they are saying / doing while the ticket runs
* Mark a ticket resolved when the run finishes
* Show a short summary of what each agent did on that ticket
* Let a human approve a pay or purchase when asked
* Show the checking balance (it should drop after an approved pay)



Make the dashboard look good! Let's be creative with teh layout and feeeeeeel - let's do a vibe of under the sea. Tell the front end to talk your backend at http://localhost:8000. On the backend, allow the Vite page origin (usually http://localhost:5173) so the browser is allowed to call those routes.

And let's start the board with:
npm run dev


Let's write output/design.md with the theme of the dashboard (layout, how agents read differenlty, how resolved tickets and cash show up) and why -- including the creative choices that make it feel special and something humans would actually enjoy using.

### What was missing after the first prompt

No follow-up prompt was needed. Two things the prompt left open were decided here:
- **"Resolved" on the board** means the crew finished its work (the Boss closed out the ticket). A gold "needs you" badge stays on a ticket until any payment is decided.
- **Per-agent summaries** come from a new `GET /tickets/{id}/summary` route.

Testing turned up two bugs that were fixed without a new prompt:
- Accounting couldn't check its cash reserve on ticket 101, because the only cash tool needed a lease id. It now has `get_cash_balance` and `list_leases`, and its prompt says a linked overdue invoice for the exact item counts as blocking the order.
- An approved customer ticket kept saying "waiting on your approval". It now moves to `waiting_on_customer`.

### Evidence

- **Dashboard:** built [`frontend/`](frontend/) (React + Vite + TypeScript), "The Coral Desk". The five agents are hand-drawn SVG sea creatures. Tickets appear as clams that open to a pearl when resolved, cash as a treasure chest that shakes and drops coins when money leaves, and payment requests as messages in bottles. A live sonar feed and a Captain's log show what each agent did. `frontend/.env` points it at `http://localhost:8000`, and `npm run dev` starts it on port 5173.
- **Backend:** CORS allows `http://localhost:5173`. Added `GET /tickets/{id}/summary` and the richer ticket `state` in [`backend/main.py`](backend/main.py), plus a new `list_leases` MCP tool.
- **Design write-up:** wrote [`output/design.md`](output/design.md). Updated [`output/harness.md`](output/harness.md) and [`mcp_server/README.md`](mcp_server/README.md).
- **Tested in the browser** against a scratch DB:
  - Ticket 102: the crew ran with live creature states, the clam opened to "Resolved", and a $2,400 bottle appeared. Approving dropped the chest from $3,400 to $1,000.
  - After a reset from the board, ticket 101 produced an $840 bottle. Approving it shook the chest, showed −$840.00, and left $2,560.
  - Ticket 103 showed every agent's summary and Delphine's draft postcard.
  - Tickets 101 and 103 also ran at the same time.
  - The mobile layout stacks into one column. Typecheck and production build pass.
- **Real data:** the real working DB is unchanged.

## Problem 9: Resolve the tickets

### Prompt(s)

Problem 9: Resolve the tickets

Let's reset the working database data/campus_customs_new.db again so we start clean.

Let's not ethe starting checking balance. Then let's run all three tickets on the board (101, 102, 103) until each is resolved.

Open output/desk_tickets.html from Problem 6. On each ticket tab, fill the actual section from this run: which agents worked, what they delegated, and which tools they used. Keep the expected section so we can compare the two.

On the Cash tab of the same output/desk_tickets.html, itemize the money:

* starting checking balance (after the reset)
* For each ticket: how cash changed when that ticket resolved, and why (which pay / purcchase, dollar amount)
* ending checking balance - it must match cash_accounts in the working database.

Wrong math will lose points even if the board shows every ticket resolved so let's be careful!!

Let's also save:

* output/resolved_tickets.json - for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals
* output/resolved_board.html - a page you can double-click with a screenshot of the React board for each resolved ticket (101, 102, 103)


Append real runs to output/audit_trail.json. Finish output/harness.md so it covers tables, MCP tools, the five agents, API routes, the dashboard, and safety rules.

### What was missing after the first prompt

No follow-up prompt was needed.
- **Closing tickets.** "Until each is resolved" needed a way for a person to mark tickets resolved that no payment closes (103, and 101 after its payment, since a drafted reply still has to be sent). I added a **Close ticket ✓** button and a `POST /tickets/{id}/close` route, which refuses while a payment is pending.
- **Who approved.** Approvals and closings were done by Claude on the board at the user's request, and signed "Claude (for Robert Daly)" so the ledger is honest about who clicked.
- **Vite fix.** The board's dev server was hanging because `my-app/node_modules/fsevents` had been offloaded by iCloud ("dataless"). A local copy of `fsevents` was placed in `frontend/node_modules`.
- **Harness recovery.** A bad edit truncated `output/harness.md` partway through. It was rebuilt by replaying every recorded edit, checked against the section line numbers printed just before the truncation, and then finished.

### Evidence

- **Reset:** the database was reset from the board. Starting checking balance: **$3,400.00**.
- **Ticket 101:** Boss → Inventory, Accounting, Customer Service. Request #1 for **$840.00** (invoice 501) was approved, leaving **$2,560.00**.
- **Ticket 102:** Boss → Facilities, Accounting. Request #2 for **$2,400.00** (lease 1 rent) was approved, leaving **$160.00**.
- **Ticket 103:** Boss → Inventory, Accounting, Customer Service, plus an extra Accounting → Inventory hop. It was a quote only, with **$0.00** change.
- **End state:** ending balance **$160.00**, which equals `cash_accounts`. `payments` has 2 rows summing to $3,240.00, and all three tickets are `resolved`.
- **Files:**
  - [`output/desk_tickets.html`](output/desk_tickets.html): Actual sections next to Expected, and the itemized Cash tab.
  - [`output/resolved_tickets.json`](output/resolved_tickets.json)
  - [`output/resolved_board.html`](output/resolved_board.html): 4 embedded board screenshots, from [`output/board_shots/`](output/board_shots/).
  - [`output/audit_trail.json`](output/audit_trail.json): 224 entries, covering the reset, the 3 runs, 2 approvals, and 2 closings.
  - [`output/harness.md`](output/harness.md): finished with tables, MCP tools, agents, routes, dashboard, safety, and the final run.

### Follow-up prompt

it can't reach the backend :(

why was 103 resolved when a human needs to review and send the email? Can you please adjust that so if it needs human review then it's a status of "Awaiting Human Input" or something like that.

can you walk me through the response to 101? It sounds like S isn't available so we would have to pay 840 for a rush reprint? Do we know how much we would make from selling this tee or no?

Can yuou open the desk_tickets.html for me in my browswer?

### What the follow-up fixed

- **Backend unreachable:** the servers had been stopped after the run, so they were restarted.
- **The status change:**
  - Tickets 101 and 103 had been closed as "resolved" even though their replies were never sent.
  - The app now has `awaiting_human_input`. The Boss must use it whenever its `needs_human` list isn't empty.
  - The board shows **Awaiting human input** (a gold clam and a "needs you" badge). A ticket only becomes resolved when a person approves with "Also close the ticket" or clicks **Human steps done ✓**, after seeing the crew's to-do list.
- **The 101 walk-through:** the $840 is an existing overdue bill for a reprint the shop already ordered. Tauhid's tee earns $28 − $8 = $20, and the database doesn't record how many shirts the reprint covers.
- **The board run was redone in Problem 11.** The user's own board testing had since reset the working DB. The final run was repeated cleanly before submission, and every Problem 9 output was regenerated from it.

## Problem 10: Reflection

### Prompt(s)

Problem 10: Reflection

Alright yo let's fill int he Reflection tab in desk_tickets.html.

Write the following:

* evaluate the perofrmance of the agents on each ticket and explain why. I personally loved that they collarborated and at the end i like that it shows the other priorities as well and the estimates.
* For each ticket, how did Actual compare to the expected plan we wrote earlier?
* What would have been simpler as one agent with tools -- and why?
* Describe 3 new problems campus customs might face that this agent team could solve with the tools you built - i think inventory vs. budget analysis for sure. I think writing messages back to users as well and having a different permissions thing where the manager has their own log in and sees all of this backend stuff.
* Describe 3 new problems campus customs might face that this agent team could not solve with the tools you built, and explain the tools and agents you would need to solve them - I think I would want an agent that learns what the humans approve and don't approve in terms of emails written that learns and gives each draft a score of what % likelihood a human will approve so the human review can hopefully get less and less over time. 



Be sure to tie every answer to this app and the 3 tickets you ran -- use the ticket tabs and cash tab on the same page as your evidence. 

Generic artificial intelligence essays without campus customs details will score looooooooowwwwww


Let's write really really well here!

### What was missing after the first prompt

No follow-up prompt was needed; the prompt gave the five questions and the user's own ideas for each list. One judgment call: the manager login is partly an app feature (sign-in) rather than an agent job. The reflection says so, and shows what the existing agents and tools already provide for a manager's view.

### Evidence

Filled the Reflection tab of [`output/desk_tickets.html`](output/desk_tickets.html), using only the Problem 9 run as evidence (ticket tabs, Cash tab, `audit_trail.json`):
- Per-ticket grades with the reasons (101 A−, 102 A, 103 B).
- A plan-vs-actual comparison table.
- The case for and against one agent with tools, using numbers from the run: 60 model requests, 153,241 input tokens, and repeated `get_ticket` calls.
- Three problems the team could solve: inventory vs. budget ($264 restock against $160 cash; $1,024 of stock at cost), follow-up messages, and a manager view.
- Three it couldn't solve, with the tables, tools, and agents each would need: a draft-approval scorer, purchasing, and sales with cash forecasting.

## Problem 11: Submit to GitHub

### Prompt(s)

Problem 11: Submit to GitHub

Let's pussssshhhhhh to a public GitHub repo so graders can clone it. 

Submit the repo URL to Canvas, and also put it in output/github_url.txt

Do not push the real .env to the GitHub repo. Do include both database files under data/ (the original and your working copy) so graders can run your app easily.

Let's goooooo!!!

### What was missing after the first prompt

The working DB no longer matched the Problem 9 write-up (the user's board testing had reset it). When asked, the user chose to re-run Problem 9 cleanly before pushing. Submitting the URL to Canvas has to be done by the user; Claude has no Canvas access.

### Evidence

- **Clean re-run on the board:**
  - Reset to $3,400.00.
  - 101: request #1, $840, approved, leaving $2,560.00. Stays `awaiting_human_input`.
  - 102: request #2, $2,400, approved and closed, leaving $160.00. `resolved`.
  - 103: a quote, $0. `awaiting_human_input`.
  - The DB `cash_accounts` shows $160.00.
- **Regenerated from that run:** `output/resolved_tickets.json`, `output/resolved_board.html` (new screenshots), the Actual/Cash/Reflection tabs of `output/desk_tickets.html`, and the final-run sections of `output/harness.md` and `output/design.md`.
- **New files:** [`README.md`](README.md) with setup steps, a `.gitignore` that keeps `.env`, `.venv/`, and `node_modules/` out, `.env.example`, `frontend/.env.example`, and [`output/github_url.txt`](output/github_url.txt).
- **Pushed** to the public repo https://github.com/rbdaly16/Campus-Customs-Agent-Team with both databases under `data/`. No `.env` was pushed.
