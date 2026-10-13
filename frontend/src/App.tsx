import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, type AgentEvent, type AgentKey, type Cash, type PaymentRequest, type Ticket, type TicketSummary } from './api'
import { Chest, Clam, Creature } from './Creatures'
import { CREW, CREW_ORDER, crewName, liveCrew, narrate, toolLabel } from './crew'

const money = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
const clock = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' })

const TICKET_BLURB: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Price request',
}
const STATE_PILL: Record<Ticket['state'], string> = {
  open: 'Open',
  running: 'Crew diving',
  awaiting_human: 'Awaiting human input',
  waiting_on_customer: 'Waiting on customer',
  resolved: 'Resolved',
}
const STATUS_WORDS: Record<string, string> = {
  open: 'Open',
  in_progress: 'In progress',
  waiting_on_customer: 'Waiting on customer',
  awaiting_human_input: 'Awaiting human input',
  resolved: 'Resolved',
}

interface Toast {
  id: number
  kind: 'pearl' | 'coin' | 'error'
  text: string
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [cashDelta, setCashDelta] = useState<number | null>(null)
  const [approvals, setApprovals] = useState<PaymentRequest[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [summary, setSummary] = useState<TicketSummary | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [offline, setOffline] = useState(false)
  const [starting, setStarting] = useState(false)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [approver, setApprover] = useState(() => localStorage.getItem('coral-approver') ?? '')

  const cursor = useRef<{ runId: string | null; after: number }>({ runId: null, after: -1 })
  const prevStates = useRef<Record<number, string>>({})
  const prevBalance = useRef<number | null>(null)

  const toast = useCallback((kind: Toast['kind'], text: string) => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, kind, text }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5200)
  }, [])

  const anyRunning = tickets.some((t) => t.state === 'running')
  const current = tickets.find((t) => t.id === selected) ?? null

  // Shop-wide state: tickets, the treasure chest, and bottles waiting for a human.
  const refreshShop = useCallback(async () => {
    try {
      const [t, c, a] = await Promise.all([api.tickets(), api.cash(), api.approvals()])
      setOffline(false)
      for (const tk of t) {
        if (prevStates.current[tk.id] === 'running' && tk.state === 'resolved') {
          toast('pearl', `Pearl found! The crew resolved ticket #${tk.id}.`)
        } else if (prevStates.current[tk.id] === 'running' && tk.state === 'awaiting_human') {
          toast('coin', `The crew surfaced on ticket #${tk.id}. It's awaiting your input.`)
        }
        prevStates.current[tk.id] = tk.state
      }
      setTickets(t)
      setApprovals(a)
      if (prevBalance.current !== null && c.balance !== prevBalance.current) {
        setCashDelta(c.balance - prevBalance.current)
        setTimeout(() => setCashDelta(null), 4000)
      }
      prevBalance.current = c.balance
      setCash(c)
      setSelected((s) => s ?? t[0]?.id ?? null)
    } catch {
      setOffline(true)
    }
  }, [toast])

  // The selected ticket's latest run: per-agent summary plus the live event stream.
  const refreshTicket = useCallback(async (ticketId: number) => {
    try {
      const s = await api.summary(ticketId)
      setSummary(s)
      if (!s.run_id) {
        cursor.current = { runId: null, after: -1 }
        setEvents([])
        return
      }
      if (cursor.current.runId !== s.run_id) {
        cursor.current = { runId: s.run_id, after: -1 }
        setEvents([])
      }
      const res = await api.events(s.run_id, cursor.current.after)
      if (cursor.current.runId !== s.run_id) return
      cursor.current.after = res.next_after
      if (res.events.length) setEvents((ev) => [...ev, ...res.events])
    } catch {
      setOffline(true)
    }
  }, [])

  useEffect(() => {
    refreshShop()
    const id = setInterval(refreshShop, anyRunning ? 1500 : 4000)
    return () => clearInterval(id)
  }, [refreshShop, anyRunning])

  const selectedRunning = current?.state === 'running' || summary?.status === 'running'
  useEffect(() => {
    if (selected === null) return
    refreshTicket(selected)
    const id = setInterval(() => refreshTicket(selected), selectedRunning ? 1200 : 5000)
    return () => clearInterval(id)
  }, [selected, selectedRunning, refreshTicket])

  const selectTicket = (id: number) => {
    if (id === selected) return
    cursor.current = { runId: null, after: -1 }
    setSummary(null)
    setEvents([])
    setSelected(id)
  }

  const startRun = async () => {
    if (!current) return
    setStarting(true)
    try {
      await api.run(current.id)
      prevStates.current[current.id] = 'running'
      await Promise.all([refreshShop(), refreshTicket(current.id)])
    } catch (e) {
      toast('error', (e as Error).message)
    } finally {
      setStarting(false)
    }
  }

  const decide = async (req: PaymentRequest, approve: boolean, resolve: boolean) => {
    const who = approver.trim()
    if (!who) return toast('error', 'Sign your name in the bottle first, so the ledger knows who approved.')
    localStorage.setItem('coral-approver', who)
    try {
      if (approve) {
        const r = await api.approve(req.id, who, resolve)
        toast('coin', `${money(r.amount)} sent. Treasure chest now holds ${money(r.balance_after)}.`)
      } else {
        await api.reject(req.id, who, 'Rejected on the Coral Desk')
        toast('pearl', `Request #${req.id} sent back. No money moved.`)
      }
    } catch (e) {
      toast('error', (e as Error).message)
    }
    await refreshShop()
    if (selected !== null) refreshTicket(selected)
  }

  const closeTicket = async () => {
    if (!current) return
    const who = approver.trim()
    if (!who) return toast('error', 'Sign your name in the bottle panel first, so the ticket note knows who finished it.')
    const todo = summary?.outcome?.needs_human ?? []
    const checklist = todo.length ? `\n\nThe crew's list for a person:\n• ${todo.join('\n• ')}` : ''
    if (!confirm(`Mark ticket #${current.id} resolved? Only do this once you've finished the human steps.${checklist}`)) return
    localStorage.setItem('coral-approver', who)
    try {
      await api.close(current.id, who, `Human steps confirmed done by ${who}${todo.length ? `: ${todo.join(' ')}` : '.'}`)
      toast('pearl', `Ticket #${current.id} resolved. Pearl secured.`)
    } catch (e) {
      toast('error', (e as Error).message)
    }
    await refreshShop()
  }

  const resetTide = async () => {
    if (!confirm('Turn the tide? This restores the shop database to its original values for a fresh run.')) return
    try {
      await api.reset(approver.trim() || 'dashboard')
      prevBalance.current = null
      cursor.current = { runId: null, after: -1 }
      setEvents([])
      setSummary(null)
      toast('pearl', 'The tide has turned. Fresh tickets, full chest.')
      await refreshShop()
      if (selected !== null) refreshTicket(selected)
    } catch (e) {
      toast('error', (e as Error).message)
    }
  }

  const live = useMemo(() => liveCrew(events), [events])
  const feed = useMemo(
    () => events.map((e) => ({ e, line: narrate(e) })).filter((x) => x.line).reverse(),
    [events],
  )
  const runDone = summary?.status === 'done'

  return (
    <div className="ocean">
      <Bubbles />
      <div className="rays" aria-hidden="true" />

      <header className="surface">
        <div className="brand">
          <h1>
            The Coral Desk <span className="wave">〰</span>
          </h1>
          <p>Campus Customs back office · twenty thousand leagues under Chapel Street · shop date {cash?.date ?? '…'}</p>
        </div>
        <button className="ghost" onClick={resetTide} disabled={anyRunning} title="Restore the original database">
          Turn the tide ↺
        </button>
      </header>

      {offline && (
        <div className="offline" role="alert">
          The reef can't reach the backend at <code>{import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}</code>. Start
          it from <code>backend/</code> with <code>uvicorn main:app --reload --port 8000</code>.
        </div>
      )}

      <main className="reef-grid">
        {/* ---------------------------------------------------------- tide pool */}
        <aside className="panel tide-pool">
          <h2>Tide pool</h2>
          <p className="hint">Pick a ticket, then send the crew.</p>
          <ul className="tickets">
            {tickets.map((t) => (
              <li key={t.id}>
                <button
                  className={`ticket ${t.state} ${t.id === selected ? 'selected' : ''}`}
                  onClick={() => selectTicket(t.id)}
                  aria-pressed={t.id === selected}
                >
                  <Clam open={t.state === 'resolved'} glowing={t.state === 'running'} waiting={t.state === 'awaiting_human'} />
                  <span className="ticket-text">
                    <span className="ticket-id">#{t.id} · {TICKET_BLURB[t.type] ?? t.type}</span>
                    <strong>{t.subject}</strong>
                    <span className="requester">{t.requester}</span>
                  </span>
                  <span className="pill-row">
                    <span className={`state-pill ${t.state}`}>{STATE_PILL[t.state]}</span>
                    {(t.pending_approvals > 0 || t.state === 'awaiting_human') && <span className="needs-you">needs you</span>}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        {/* ---------------------------------------------------------- center: ticket + crew */}
        <section className="center">
          {current && (
            <div className="panel ticket-card">
              <div className="ticket-head">
                <div>
                  <span className="ticket-id">Ticket #{current.id} · {TICKET_BLURB[current.type] ?? current.type}</span>
                  <h2>{current.subject}</h2>
                  <p className="requester">from {current.requester}</p>
                </div>
                <div className="ticket-actions">
                  <button className="dive" onClick={startRun} disabled={starting || current.state === 'running'}>
                    {current.state === 'running' ? 'Crew is diving…' : runDone ? 'Send the crew again' : 'Send the crew ↓'}
                  </button>
                  {(current.state === 'awaiting_human' || current.state === 'waiting_on_customer') && current.pending_approvals === 0 && (
                    <button className="close-ticket" onClick={closeTicket} title="I've finished the human steps (e.g. sent the reply)">
                      Human steps done ✓
                    </button>
                  )}
                </div>
              </div>
              <div className="facts">
                {current.sku && <Fact label="Item" value={`${current.sku} · size ${current.size} · qty ${current.qty}`} />}
                {current.invoice_id && <Fact label="Linked invoice" value={`#${current.invoice_id}`} />}
                {current.lease_id && <Fact label="Linked lease" value={`#${current.lease_id}`} />}
                <Fact label="Status" value={STATUS_WORDS[current.status] ?? current.status} />
              </div>
              <NoteLines notes={current.notes} />
            </div>
          )}

          <div className="panel reef">
            <h2>The crew</h2>
            <div className="crew">
              {CREW_ORDER.map((k) => (
                <CrewCard key={k} agent={k} state={live.crew[k]} active={live.active === k && selectedRunning} />
              ))}
            </div>
          </div>

          {summary && summary.status !== 'never_run' && (
            <CaptainsLog summary={summary} />
          )}

          <div className="panel sonar">
            <h2>
              Sonar feed {selectedRunning && <span className="ping" aria-label="live" />}
            </h2>
            {feed.length === 0 ? (
              <p className="hint">Quiet waters. Send the crew to hear them work.</p>
            ) : (
              <ol className="feed">
                {feed.map(({ e, line }) => (
                  <li key={e.index} className={`feed-line ${e.agent}`} style={{ ['--c' as string]: e.agent in CREW ? CREW[e.agent as AgentKey].color : '#ffd166' }}>
                    <span className="feed-time">{clock(e.time)}</span>
                    <span className="feed-who">{e.agent === 'human' ? 'You' : crewName(e.agent)}</span>
                    <span className="feed-text">{line}</span>
                    {e.event === 'mcp_tool_call' && <code className="tool-chip">{String(e.detail.tool)}</code>}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </section>

        {/* ---------------------------------------------------------- right: chest + bottles */}
        <aside className="right">
          <div className={`panel treasure ${cashDelta !== null && cashDelta < 0 ? 'spending' : ''}`}>
            <Chest shaking={cashDelta !== null} />
            <div>
              <h2>Treasure chest</h2>
              <p className="balance" aria-live="polite">{cash ? money(cash.balance) : '…'}</p>
              <p className="hint">checking · as of {cash?.date ?? '…'}</p>
              {cashDelta !== null && <span className={`delta ${cashDelta < 0 ? 'down' : 'up'}`}>{cashDelta < 0 ? '−' : '+'}{money(Math.abs(cashDelta))}</span>}
            </div>
            {cashDelta !== null && cashDelta < 0 && (
              <div className="coins" aria-hidden="true">
                {[0, 1, 2, 3, 4].map((i) => <i key={i} style={{ ['--i' as string]: i }} />)}
              </div>
            )}
          </div>

          <div className="panel bottles">
            <h2>Messages in bottles</h2>
            <p className="hint">The crew can only <em>prepare</em> a payment. Nothing leaves the chest until you approve.</p>
            <label className="sign">
              Signed by
              <input value={approver} onChange={(e) => setApprover(e.target.value)} placeholder="Your name" />
            </label>
            {approvals.length === 0 ? (
              <p className="empty-bottle">No bottles washed up. Nothing waiting for you.</p>
            ) : (
              approvals.map((r) => <Bottle key={r.id} req={r} cash={cash} onDecide={decide} />)
            )}
          </div>
        </aside>
      </main>

      <div className="seafloor" aria-hidden="true">
        <Seaweed />
      </div>

      <div className="toasts" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.kind}`}>{t.text}</div>
        ))}
      </div>
    </div>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="fact">
      <span>{label}</span>
      {value}
    </div>
  )
}

function NoteLines({ notes }: { notes: string | null }) {
  if (!notes) return null
  const lines = notes.split('\n')
  return (
    <ul className="notes">
      {lines.map((l, i) => {
        const m = l.match(/^\[(\S+) (.+?)\] (.*)$/)
        return (
          <li key={i}>
            {m ? (
              <>
                <span className="note-by">{m[2]}</span> {m[3]}
              </>
            ) : (
              <>
                <span className="note-by">Original note</span> {l}
              </>
            )}
          </li>
        )
      })}
    </ul>
  )
}

function CrewCard({ agent, state, active }: { agent: AgentKey; state: { status: string; line: string; tools: number }; active: boolean }) {
  const m = CREW[agent]
  return (
    <div className={`crew-card ${state.status} ${active ? 'active' : ''}`} style={{ ['--c' as string]: m.color }}>
      <div className="speech" aria-live={active ? 'polite' : 'off'}>{state.line}</div>
      <div className="creature-wrap">
        <Creature agent={agent} color={m.color} size={78} />
        {active && (
          <div className="mini-bubbles" aria-hidden="true">
            <i /><i /><i />
          </div>
        )}
      </div>
      <strong>{m.name}</strong>
      <span className="role">{m.role}</span>
      <span className="crew-status">
        {active ? 'talking now' : state.status === 'working' ? 'waiting on a teammate' : state.status === 'done' ? `done · ${state.tools} tool calls` : 'resting'}
      </span>
    </div>
  )
}

function CaptainsLog({ summary }: { summary: TicketSummary }) {
  const used = summary.agents.filter((a) => a.times_called > 0)
  const draft = summary.outcome?.customer_message ?? used.find((a) => a.customer_message)?.customer_message
  return (
    <div className="panel log">
      <h2>Captain's log {summary.status === 'running' && <span className="tag">being written…</span>}</h2>
      {summary.outcome && (
        <p className="decision">
          <span className="final">{STATUS_WORDS[summary.outcome.final_status] ?? summary.outcome.final_status}</span>
          {summary.outcome.decision}
        </p>
      )}
      {summary.status === 'error' && <p className="decision error">The dive was cut short: {summary.error}</p>}
      <ul className="log-rows">
        {used.map((a) => (
          <li key={a.agent} style={{ ['--c' as string]: CREW[a.agent].color }}>
            <Creature agent={a.agent} color={CREW[a.agent].color} size={40} />
            <div>
              <strong>{CREW[a.agent].name}</strong> <span className="role">{CREW[a.agent].role}</span>
              <p>{a.summary ?? 'Still working…'}</p>
              <div className="chips">
                {a.tools.map((t) => (
                  <span key={t} className="chip" title={t}>{toolLabel(t)}</span>
                ))}
                {a.handed_to.map((t, i) => (
                  <span key={t + i} className="chip handoff">→ {crewName(t)}</span>
                ))}
              </div>
            </div>
          </li>
        ))}
      </ul>
      {draft && (
        <div className="postcard">
          <span className="postcard-label">Delphine's draft · a person reviews and sends it</span>
          <p>{draft}</p>
        </div>
      )}
      {summary.outcome && summary.outcome.needs_human.length > 0 && (
        <div className="for-you">
          <span>For you</span>
          <ul>{summary.outcome.needs_human.map((n) => <li key={n}>{n}</li>)}</ul>
        </div>
      )}
    </div>
  )
}

function Bottle({ req, cash, onDecide }: { req: PaymentRequest; cash: Cash | null; onDecide: (r: PaymentRequest, approve: boolean, resolve: boolean) => void }) {
  const [busy, setBusy] = useState(false)
  // Rent is the whole ticket; an invoice on a customer order usually still leaves a reply to send.
  const [resolve, setResolve] = useState(req.kind === 'rent')
  const after = cash ? cash.balance - req.amount : null
  const act = async (approve: boolean) => {
    setBusy(true)
    await onDecide(req, approve, resolve)
    setBusy(false)
  }
  return (
    <div className="bottle">
      <div className="bottle-head">
        <span className="cork" aria-hidden="true" />
        <span>Request #{req.id} · ticket #{req.ticket_id}</span>
      </div>
      <p className="bottle-amount">{money(req.amount)}</p>
      <p className="bottle-what">
        {req.kind === 'rent' ? `Rent for lease #${req.ref_id}` : `Vendor invoice #${req.ref_id}`} · from {req.account}
      </p>
      {req.reason && <p className="bottle-reason">“{req.reason}”</p>}
      <p className="bottle-by">
        Prepared by {req.requested_by.replace(' agent', '') === 'accounting' ? 'Shelly (Accounting)' : req.requested_by}
        {after !== null && <> · chest after: <b className={after < 500 ? 'low' : ''}>{money(after)}</b></>}
      </p>
      <label className="resolve-box">
        <input type="checkbox" checked={resolve} onChange={(e) => setResolve(e.target.checked)} /> Also close the ticket
      </label>
      <div className="bottle-actions">
        <button className="approve" disabled={busy} onClick={() => act(true)}>Approve & pay</button>
        <button className="reject" disabled={busy} onClick={() => act(false)}>Send back</button>
      </div>
    </div>
  )
}

function Bubbles() {
  const bubbles = useMemo(
    () => Array.from({ length: 26 }, (_, i) => ({ left: (i * 37) % 100, size: 4 + ((i * 7) % 14), delay: (i * 1.7) % 14, dur: 9 + ((i * 3) % 10) })),
    [],
  )
  return (
    <div className="bubbles" aria-hidden="true">
      {bubbles.map((b, i) => (
        <span key={i} style={{ left: `${b.left}%`, width: b.size, height: b.size, animationDelay: `${b.delay}s`, animationDuration: `${b.dur}s` }} />
      ))}
    </div>
  )
}

function Seaweed() {
  return (
    <svg viewBox="0 0 1200 120" preserveAspectRatio="none" className="weeds">
      {Array.from({ length: 18 }, (_, i) => {
        const x = 20 + i * 68
        const h = 60 + ((i * 29) % 50)
        return (
          <path
            key={i}
            className="weed"
            style={{ animationDelay: `${(i % 5) * 0.6}s` }}
            d={`M${x} 120 C${x - 14} ${120 - h / 3} ${x + 14} ${120 - (2 * h) / 3} ${x} ${120 - h}`}
            stroke={i % 3 ? '#1f8a6a' : '#2fb58a'}
            strokeWidth="7"
            fill="none"
            strokeLinecap="round"
          />
        )
      })}
      <path d="M0 110 C200 96 400 118 600 106 C800 94 1000 116 1200 104 L1200 120 L0 120 Z" fill="#c9b48a" opacity=".55" />
    </svg>
  )
}
