# The Coral Desk: dashboard design

The Campus Customs agent dashboard ([`../frontend/`](../frontend/), React + Vite + TypeScript) is themed as an **under-the-sea back office**. The shop's back room sits "twenty thousand leagues under Chapel Street." Tickets wash into a tide pool, a crew of five sea creatures dives in to work each one, the shop's cash sits in a treasure chest, and anything that needs a human floats up as a message in a bottle.

**Why the theme:** an agent dashboard is mostly *waiting and watching*. A ticket takes a minute or two while agents hand work to each other. An ocean makes that wait feel calm instead of anxious, because things drift, bob, and surface in their own time. The metaphor also maps cleanly onto the mechanics: diving in (starting a run), surfacing (an agent finishing), pearls (resolved), and bottles (requests from below that need someone on shore).

## Layout

Three columns on a deep-water gradient. Below 1180 px wide they stack into one column.

| Column | What lives there | Why |
| --- | --- | --- |
| **Left: Tide pool** | The three tickets as clam cards: id, type, subject, requester, a state pill, and a "needs you" badge | It is the queue. You always see every ticket and its state at a glance, and you pick one here. |
| **Center: the dive** | The selected ticket card (facts, signed note history, and the big gold **Send the crew ↓** button), then **The crew** (five creatures), the **Captain's log** (per-agent summary), and the **Sonar feed** (the live event stream) | This is where attention goes during a run. It reads top to bottom: what the ticket is, who is working on it, what they concluded, and every step they took. |
| **Right: shore** | The **Treasure chest** (checking balance) and **Messages in bottles** (payment requests waiting for approval) | Money and human decisions stay pinned to one side, so they are never scrolled away while you watch a run. |

The header holds the title, the shop's own date (2026-08-31, from the desk table, not the real clock), and **Turn the tide ↺**, which resets the database for a fresh run. It is disabled while a crew is diving and asks for confirmation first.

## How the agents read differently

Each agent is a hand-drawn SVG sea creature (no image generation) with its own color, used everywhere that agent appears: crew card, speech bubble ring, log row, feed line, and hand-off chips. Each creature was chosen to fit its job:

| Agent | Creature | Color | Why this creature |
| --- | --- | --- | --- |
| Boss | **Captain Bluefin**, a whale | periwinkle blue | The biggest creature, sees the whole reef, and its spout puffs when it is talking. |
| Inventory | **Ollie**, an octopus | coral pink | Eight arms on eight shelves. Its arms wiggle while it counts stock. |
| Accounting | **Shelly**, a sea turtle | sea green | Slow and steady with money, which is what you want from the agent that prepares payments. |
| Facilities | **Hermie**, a hermit crab | sandy orange | A hermit crab knows all about homes and leases. Its claw snaps while it checks the rent notice. |
| Customer Service | **Delphine**, a dolphin | aqua | Friendly and talkative, and the voice customers actually hear. |

Each crew card has four states, so you can tell at a glance who is doing what:
- **resting** (dimmed, italic idle line such as "Eight arms on the shelves"): not called yet.
- **talking now** (lifted, glowing ring in its color, swimming animation, bubbles rising): the agent whose model is producing the current step.
- **waiting on a teammate** (gentle bob, colored outline): the agent handed work off and is waiting for the reply. Watching the Boss sit in this state while Ollie talks *is* the delegation chain made visible.
- **done · N tool calls**: the agent surfaced. Its bubble now holds its own one-line summary.

The speech bubble above each creature shows what the agent is *doing* in plain words rather than tool ids: "counting shelf stock…", "checking rent & cash…", or "asks Shelly: '…'". The raw tool name is still available as a monospace chip in the sonar feed for anyone auditing.

## How resolved (and not-yet-resolved) tickets show up

- Every ticket card has a **clam**. Open tickets show a closed clam. While the crew works, the clam bobs and glows aqua, and the pill pulses **Crew diving**. When the run finishes, one of two things happens. If a person still has something to do, the clam stays closed and glows **gold**, the pill reads **Awaiting human input**, and a **needs you** badge sits beside it. Only when nothing is left for anyone does the clam **open to reveal a pearl**, with a pearl-white **Resolved** pill and a toast: *"Pearl found!"*
- **Why two states:** a crew that has *finished* isn't the same as a ticket that is *done*. In the final run, ticket 103's crew finished in seconds, but the offer to the Yale AI Club still has to be sent by a person. Calling that "resolved" would hide work from the shop. The pearl is earned only when the human part is done too.
- A person finishes a ticket in one of two ways. Approving a payment with **Also close the ticket** checked fits rent, where the approval is the last step. Or they click **Human steps done ✓** on the ticket card, which first shows the crew's to-do list ("Review and send the drafted reply to Yale AI Club…") and asks them to confirm. Either way, the database status becomes `resolved` with a signed note.
- The **Captain's log** shows the Boss's final status and decision, then one row per agent that worked the ticket: its summary in its own words, chips for the tools it used ("reading the invoice", "pricing a quote"), and hand-off chips ("→ Shelly"). Delphine's customer draft appears as a slightly tilted **postcard**, labeled "a person reviews and sends it", so nobody thinks it has already been sent. Anything the crew flagged for a person is gathered in a dashed gold **For you** box.

## How cash shows up

- The **treasure chest** shows the checking balance in large gold numbers, with the "as of" date from `cash_accounts`.
- Payment requests arrive as **messages in bottles** that wash up with a little bounce. Each bottle shows the amount, what it pays (rent for lease #1, or vendor invoice #501), the account, the turtle's reason in her own words, and **what the chest would hold afterward** (shown in red when it would drop below $500). That way the approver sees the consequence before clicking.
- The crew can only *prepare* a bottle; the panel says so in plain words. You sign your name once (it is remembered) and click **Approve & pay** or **Send back**. Approving is the only action on the board that moves money.
- When cash goes down, the chest **shakes, gold coins sink out of it**, and a red **−$2,400.00** chip appears next to the new balance. A toast confirms the amount and the new total. Spending money should never feel invisible, and the animation makes it unmistakable that something irreversible just happened.

## Choices that make it feel special

- **Ambient life, not decoration.** Light rays slowly sway, bubbles rise across the whole page, and seaweed sways along a sandy floor. All of it sits behind the panels, carries no information, and stays out of the way. Panels are frosted "aquarium glass" (a translucent blur), so the ocean shows through without hurting readability.
- **Motion carries meaning.** Every animation maps to a state: swimming means talking, bobbing means waiting, a gold-glowing clam means a person is needed, a clam opening means resolved, a bottle washing up means it needs you, coins sinking means money left. Nothing moves just to move.
- **Plain-language narration.** The sonar feed reads like a story ("Hermie dives in for Captain Bluefin", "Shelly asks Ollie: '…'", "surfaces: '…'"), with timestamps and each line tinted in the speaker's color, newest at the top.
- **Friendly type.** Fredoka (rounded, playful) for headings and numbers, Nunito for body text. Both are soft and readable, and fit the aquarium mood.
- **Humane safety.** The two scary actions, paying and resetting, are the two places the board slows you down: a signed name on every approval, a "what the chest will hold after" preview, and a confirmation before turning the tide.
- **Accessible by default.**
  - Every animation is turned off under `prefers-reduced-motion`.
  - Agents are told apart by name and role text, not just color.
  - Live regions announce the speaking agent, the balance, and toasts.
  - Buttons have visible focus rings.
  - Text on the frosted panels stays light-on-dark with strong contrast.

## How it talks to the backend

The board calls the FastAPI routes from Problem 7 at `VITE_API_URL` (set in `frontend/.env`, default `http://localhost:8000`). The backend allows the Vite origin `http://localhost:5173` (and other localhost ports, in case Vite moves).

| Board needs | Route | How often |
| --- | --- | --- |
| Tickets, chest, bottles | `GET /tickets`, `GET /cash`, `GET /approvals` | Every 4 s; every 1.5 s while any crew is diving |
| Selected ticket's per-agent log | `GET /tickets/{id}/summary` | Every 5 s; every 1.2 s while that ticket runs |
| Live events | `GET /events?run_id=…&after=N` | Only events newer than the cursor, so the feed grows without re-downloading |
| Send the crew | `POST /tickets/{id}/run` | On click |
| Approve or send back | `POST /approvals/{id}/approve` or `/reject` | On click |
| Turn the tide | `POST /reset` | On click, after a confirmation |

If the backend is down, a red banner explains how to start it, instead of the board silently showing nothing.
