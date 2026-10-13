// Who's who on the reef: each agent is a sea creature with its own color and voice.
import type { AgentEvent, AgentKey } from './api'

export interface CrewMember {
  name: string
  creature: string
  role: string
  color: string
  idle: string
}

export const CREW: Record<AgentKey, CrewMember> = {
  boss: { name: 'Captain Bluefin', creature: 'whale', role: 'Boss', color: '#7aa8ff', idle: 'Watching the whole reef' },
  inventory: { name: 'Ollie', creature: 'octopus', role: 'Inventory', color: '#ff8fa3', idle: 'Eight arms on the shelves' },
  accounting: { name: 'Shelly', creature: 'turtle', role: 'Accounting', color: '#52e3a4', idle: 'Slow and steady with the ledger' },
  facilities: { name: 'Hermie', creature: 'crab', role: 'Facilities', color: '#ffb067', idle: 'Knows every shell and lease' },
  customer_service: { name: 'Delphine', creature: 'dolphin', role: 'Customer Service', color: '#5fe6f2', idle: 'Ready with a friendly word' },
}

export const CREW_ORDER: AgentKey[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export const TOOL_LABELS: Record<string, string> = {
  get_shop_date: 'checking the tide clock',
  list_open_tickets: 'scanning the open tickets',
  list_tickets: 'scanning all tickets',
  get_ticket: 'reading the ticket',
  get_stock_for_sku_and_size: 'counting shelf stock',
  list_vendors: 'looking up vendors',
  get_invoice_and_vendor: 'reading the invoice',
  get_rent_due_and_cash_balance: 'checking rent & cash',
  get_unit_cost_and_list_price: 'looking up price & cost',
  quote_price_for_quantity: 'pricing a quote',
  list_payments: 'checking past payments',
  list_payment_requests: 'checking pending requests',
  request_payment_approval: 'preparing a payment for you',
  update_ticket: 'updating the ticket',
  get_cash_balance: 'checking the treasure chest',
  delegate: 'handing off',
}

export const toolLabel = (tool: string) => TOOL_LABELS[tool] ?? tool.replaceAll('_', ' ')

export const crewName = (key: string) => (key in CREW ? CREW[key as AgentKey].name : key)

const clip = (s: string, n = 160) => (s.length > n ? s.slice(0, n - 1) + '…' : s)

/** A one-line, human sentence for a feed event, or null for loop plumbing we don't show. */
export function narrate(e: AgentEvent): string | null {
  const d = e.detail as Record<string, any>
  switch (e.event) {
    case 'ticket_start':
      return `The crew is called for ticket #${e.ticket_id}.`
    case 'agent_start':
      return e.parent ? `dives in for ${crewName(e.parent)}.` : 'takes the ticket.'
    case 'loop_model_response':
      return e.said ? `“${clip(e.said)}”` : null
    case 'mcp_tool_call':
      return `${toolLabel(String(d.tool))}…`
    case 'mcp_tool_blocked':
      return `was stopped by a guardrail: ${d.reason}`
    case 'mcp_tool_error':
      return `hit a snag with ${toolLabel(String(d.tool))}.`
    case 'delegation':
      return `asks ${crewName(String(d.to))}: “${clip(String(d.task ?? ''), 140)}”`
    case 'delegation_refused':
      return `couldn't hand off to ${crewName(String(d.to))}: ${d.reason}`
    case 'agent_end':
      return e.said ? `surfaces: “${clip(e.said, 220)}”` : 'surfaces.'
    case 'agent_error':
    case 'ticket_error':
      return `ran into trouble: ${clip(String(d.error ?? ''))}`
    default:
      return e.agent === 'human' ? e.said : null
  }
}

export interface LiveState {
  status: 'idle' | 'working' | 'done'
  line: string
  tools: number
}

/** Fold a run's events into what each creature is doing right now. */
export function liveCrew(events: AgentEvent[]): { crew: Record<AgentKey, LiveState>; active: AgentKey | null } {
  const crew = Object.fromEntries(
    CREW_ORDER.map((k) => [k, { status: 'idle', line: CREW[k].idle, tools: 0 } as LiveState]),
  ) as Record<AgentKey, LiveState>
  const depth: Record<string, number> = {}
  let active: AgentKey | null = null
  for (const e of events) {
    if (e.agent === 'human' || !(e.agent in crew)) continue
    const c = crew[e.agent]
    if (e.event === 'agent_start') {
      depth[e.agent] = (depth[e.agent] ?? 0) + 1
      c.status = 'working'
    } else if (e.event === 'agent_end' || e.event === 'agent_error') {
      depth[e.agent] = Math.max(0, (depth[e.agent] ?? 1) - 1)
      if (!depth[e.agent]) c.status = 'done'
    }
    if (e.event === 'mcp_tool_call') c.tools += 1
    // In the speech bubble, a finished agent just says its summary (the feed keeps "surfaces:").
    const line = e.event === 'agent_end' && e.said ? e.said : narrate(e)
    if (line) c.line = line
    active = c.status === 'working' ? e.agent : active
  }
  // The deepest agent still working is the one actually "talking" right now.
  if (active && crew[active].status !== 'working') active = null
  return { crew, active }
}
