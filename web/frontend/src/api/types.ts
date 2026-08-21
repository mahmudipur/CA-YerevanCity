export interface OrderItem {
  id: string
  name: string
  quantity: number
  unit: string | null
  unit_price: number
  total_price: number
  discount: number
  net_price: number
  is_canceled: boolean
  image?: string | null
  price?: number
  service?: number
  assignments?: Record<string, number>
  assignment_weights?: Record<string, number>
  split_method?: string
}

export interface Order {
  order_id: string
  create_date: string | null
  finish_date: string | null
  status: number
  status_label: string
  is_delivery: boolean
  payment_method: number
  payment_label: string
  branch_address: string
  total_price: number
  total_to_pay: number
  delivery_fee: number
  service_fee: number
  driver_tip: number
  items: OrderItem[]
}

export interface OrderSummary {
  order_id: string
  create_date: string | null
  total_to_pay: number
  status: number
  is_delivery: boolean
}

export type SplitMode = 'equal' | 'percentage' | 'amount' | 'part'

export interface SessionView {
  session_id: string
  kind: 'yc' | 'manual'
  order_id: string | null
  session_name: string | null
  order: Order | null
  participants: string[]
  items: OrderItem[]
  active_item_count: number
  assigned_count: number
  fee_allocations: Record<string, PersonFees> | null
  totals: Record<string, PersonTotal> | null
  currency: Currency | null
  saved_path: string | null
}

export interface PersonFees {
  delivery: number
  service: number
  driver_tip: number
  total: number
}

export interface PersonTotal {
  items: number
  fees: number
  total: number
}

export type Currency =
  | { method: 'cash' }
  | {
      method: 'revolut'
      rate: number
      eur_paid: number
      is_weekend: boolean
      eur_fee: number
      is_fair_usage: boolean
      eur_fair_usage_fee: number
      eur_effective: number
      eur_per_person: Record<string, number>
    }

export interface AssignResult {
  assignments: Record<string, number>
  assignment_weights: Record<string, number>
  split_method: string
}

export interface AssignResponse {
  index: number
  result: AssignResult
  next_index: number | null
  all_assigned: boolean
}

export interface ItemDetailResponse {
  index: number
  total: number
  item: OrderItem
  participants: string[]
  current_assignment: AssignResult | null
}

export interface ReviewRow {
  index: number
  item: OrderItem
  assignment: AssignResult | null
}

export interface ReviewResponse {
  items: ReviewRow[]
  all_assigned: boolean
}

export interface FinishResponse {
  fee_allocations: Record<string, PersonFees>
  totals: Record<string, PersonTotal>
  grand_total: number
  order_total: number
  discrepancy: number
  discrepancy_warning: boolean
}

export interface SaveResponse {
  split_id: string
  saved_path: string
  split: Record<string, unknown>
}

export interface HistoryRow {
  id: string
  split_date: string | null
  participants: string[]
  order_total: number | null
  status_label: string | null
  session_name: string | null
}

export interface AuthStatus {
  authenticated: boolean
  phone_e164: string | null
  phone_local: string | null
}
