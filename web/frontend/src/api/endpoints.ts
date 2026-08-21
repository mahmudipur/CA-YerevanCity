import { api } from './client'
import type {
  AssignResponse,
  AuthStatus,
  FinishResponse,
  HistoryRow,
  ItemDetailResponse,
  Order,
  OrderSummary,
  ReviewResponse,
  SaveResponse,
  SessionView,
  SplitMode,
} from './types'

export const authApi = {
  status: () => api.get<AuthStatus>('/auth/status'),
  sendCode: (phone_local?: string, phone_e164?: string) =>
    api.post<{ sent: boolean; phone_e164: string }>('/auth/send-code', { phone_local, phone_e164 }),
  verify: (code: string, phone_e164?: string) =>
    api.post<{ authenticated: boolean }>('/auth/verify', { code, phone_e164 }),
  logout: () => api.post<{ authenticated: boolean }>('/auth/logout'),
}

export const ordersApi = {
  list: (page = 1, count = 20) => api.get<OrderSummary[]>(`/orders?page=${page}&count=${count}`),
  latest: (refresh = false) => api.get<Order>(`/orders/latest?refresh=${refresh}`),
  fetch: (orderId: string, refresh = false) => api.get<Order>(`/orders/${orderId}?refresh=${refresh}`),
}

export const sessionsApi = {
  create: (body: { kind: 'yc' | 'manual'; order_id?: string; session_name?: string }) =>
    api.post<SessionView>('/sessions', body),
  get: (id: string) => api.get<SessionView>(`/sessions/${id}`),
  setRoster: (id: string, temp_participants: string[]) =>
    api.post<SessionView>(`/sessions/${id}/roster`, { temp_participants }),
  addManualItem: (id: string, body: { name: string; price: number; service_raw: string }) =>
    api.post<SessionView>(`/sessions/${id}/items`, body),
  importItems: (id: string, items: { name: string; price: number; service?: number | string | null }[]) =>
    api.post<SessionView>(`/sessions/${id}/items/import`, { items }),
  removeManualItem: (id: string, index: number) => api.del<SessionView>(`/sessions/${id}/items/${index}`),
  getItem: (id: string, index: number) => api.get<ItemDetailResponse>(`/sessions/${id}/items/${index}`),
  assignItem: (
    id: string,
    index: number,
    body: { mode: SplitMode; selected: string[]; values: Record<string, number> },
  ) => api.post<AssignResponse>(`/sessions/${id}/items/${index}/assign`, body),
  review: (id: string) => api.get<ReviewResponse>(`/sessions/${id}/review`),
  finish: (id: string) => api.post<FinishResponse>(`/sessions/${id}/finish`),
  save: (id: string) => api.post<SaveResponse>(`/sessions/${id}/save`),
}

export const paymentApi = {
  cash: (id: string) => api.post(`/sessions/${id}/payment`, { method: 'cash' }),
  revolut: (
    id: string,
    body: { rate: number; eur_paid: number; is_weekend: boolean; is_fair_usage: boolean },
  ) => api.post(`/sessions/${id}/payment`, { method: 'revolut', ...body }),
}

export const historyApi = {
  list: () => api.get<HistoryRow[]>('/history'),
  get: (id: string) => api.get<Record<string, unknown>>(`/history/${id}`),
  edit: (id: string) => api.post<SessionView>(`/history/${id}/edit`),
}

export function csvDownloadUrl(splitId: string) {
  return `/api/sessions/${splitId}/csv`
}

export const receiptApi = {
  getPrompt: () => api.get<{ prompt: string }>('/receipt-prompt'),
}
