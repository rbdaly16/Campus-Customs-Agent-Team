// Thin client for the Campus Customs FastAPI backend (backend/main.py).
export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type AgentKey = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: string
  notes: string | null
  created_at: string
  state: 'open' | 'running' | 'awaiting_human' | 'waiting_on_customer' | 'resolved'
  agents_running: boolean
  pending_approvals: number
}

export interface Cash {
  name: string
  balance: number
  date: string
}

export interface PaymentRequest {
  id: number
  ticket_id: number | null
  kind: 'invoice' | 'rent'
  ref_id: number
  amount: number
  account: string
  reason: string | null
  requested_by: string
  requested_at: string
  status: 'pending' | 'approved' | 'rejected'
}

export interface AgentEvent {
  index: number
  time: string
  run_id: string
  ticket_id: number | null
  agent: AgentKey | 'human'
  parent: string | null
  step: number | null
  event: string
  said: string | null
  tools: string[]
  detail: Record<string, unknown>
}

export interface AgentSummary {
  agent: AgentKey
  times_called: number
  summary: string | null
  tools: string[]
  handed_to: AgentKey[]
  actions: string[]
  needs_human: string[]
  customer_message: string | null
}

export interface TicketOutcome {
  ticket_id: number
  final_status: string
  decision: string
  actions_taken: string[]
  delegated_to: AgentKey[]
  customer_message: string | null
  needs_human: string[]
}

export interface TicketSummary {
  ticket_id: number
  run_id: string | null
  status: 'never_run' | 'running' | 'done' | 'error'
  started_at?: string
  finished_at?: string | null
  outcome: TicketOutcome | null
  error?: string | null
  agents: AgentSummary[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_URL + path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    let detail: unknown
    try {
      detail = (await res.json()).detail
    } catch {
      /* body wasn't JSON */
    }
    throw new Error(typeof detail === 'string' ? detail : `${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  tickets: () => request<{ tickets: Ticket[] }>('/tickets').then((r) => r.tickets),
  cash: () => request<Cash>('/cash'),
  approvals: () => request<{ requests: PaymentRequest[] }>('/approvals?status=pending').then((r) => r.requests),
  summary: (ticketId: number) => request<TicketSummary>(`/tickets/${ticketId}/summary`),
  events: (runId: string, after: number) =>
    request<{ next_after: number; events: AgentEvent[] }>(`/events?run_id=${runId}&after=${after}&limit=1000`),
  run: (ticketId: number) =>
    request<{ run_id: string }>(`/tickets/${ticketId}/run`, { method: 'POST' }),
  approve: (id: number, approvedBy: string, resolveTicket: boolean) =>
    request<{ amount: number; balance_after: number }>(`/approvals/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved_by: approvedBy, resolve_ticket: resolveTicket }),
    }),
  reject: (id: number, rejectedBy: string, reason: string) =>
    request(`/approvals/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ rejected_by: rejectedBy, reason }),
    }),
  close: (ticketId: number, closedBy: string, note: string) =>
    request(`/tickets/${ticketId}/close`, { method: 'POST', body: JSON.stringify({ closed_by: closedBy, note }) }),
  reset: (by: string) => request('/reset', { method: 'POST', body: JSON.stringify({ reset_by: by }) }),
}
