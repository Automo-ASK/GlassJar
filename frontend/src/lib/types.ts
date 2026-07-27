export type CustomFieldType = 'text' | 'number' | 'phone' | 'email' | 'select' | 'checkbox'

export interface CustomFieldDef {
  key: string
  label: string
  type: CustomFieldType
  required: boolean
  options?: string[] | null
}

export type MemberRole = 'admin' | 'treasurer' | 'member'
export type CollectionStatus = 'draft' | 'active' | 'closed'
export type MemberPaymentStatus = 'pending' | 'paid' | 'waived'
export type PaymentStatus = 'pending' | 'paid' | 'failed' | 'reversed'
export type ManualChannel = 'manual_cash' | 'manual_transfer'
export type ExpenseStatus = 'pending' | 'awaiting_otp' | 'paid_out' | 'failed'
export type LedgerEntryType = 'credit' | 'debit'

export interface User {
  id: number
  email: string
  full_name: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface ReservedAccount {
  bank_name: string
  account_number: string
  account_name: string
  status: 'active' | 'pending' | 'failed'
}

export interface Community {
  id: number
  name: string
  description: string | null
  invite_code: string
  created_by: number
  reserved_account?: ReservedAccount | null
}

// A roster entry. `user_id` is null until the person claims it with an account.
export interface CommunityMember {
  id: number
  community_id: number
  user_id: number | null
  display_name: string
  email?: string | null
  phone?: string | null
  role: MemberRole
  is_claimed: boolean
}

export interface UnclaimedMember {
  id: number
  display_name: string
}

export interface CommunityLookup {
  id: number
  name: string
  description: string | null
  unclaimed_members: UnclaimedMember[]
}

export interface Collection {
  id: number
  community_id: number
  title: string
  description: string | null
  amount_per_member: number
  target_amount: number | null
  deadline: string | null
  budget_allocation: Record<string, number> | null
  custom_fields: CustomFieldDef[] | null
  status: CollectionStatus
  share_token: string
  created_by: number
  created_at: string
}

export interface CollectionMemberEntry {
  id: number
  collection_id: number
  member_id: number
  display_name: string
  amount_due: number
  status: MemberPaymentStatus
  paid_at: string | null
  note: string | null
}

export interface CollectionDetail extends Collection {
  entries: CollectionMemberEntry[]
}

export interface ActiveCollectionSummary {
  id: number
  title: string
  target_amount: number | null
  amount_collected: number
  paid_count: number
  pending_count: number
}

export interface LedgerEntryOut {
  id: number
  type: LedgerEntryType
  amount: number
  reference_type: string
  reference_id: number
  description: string | null
  created_at: string
}

export interface CommunityDashboard {
  treasury_balance: number
  active_collections: ActiveCollectionSummary[]
  pending_expenses_count: number
  recent_ledger: LedgerEntryOut[]
}

export interface Expense {
  id: number
  community_id: number
  collection_id: number | null
  title: string
  amount: number
  category: string
  status: ExpenseStatus
  receipt_url: string | null
  requested_by: number
  created_at: string
  destination_bank_name: string | null
  destination_bank_code: string | null
  destination_account_number: string | null
  destination_account_name: string | null
  payout_reference: string | null
  payout_error: string | null
  manual_payout: boolean
  paid_out_at: string | null
  paid_out_by: number | null
}

export interface Bank {
  code: string
  name: string
}

export interface AccountLookup {
  account_number: string
  account_name: string
  bank_code: string
}

export interface LedgerResponse {
  entries: LedgerEntryOut[]
  balance: number
  total: number
}

export interface TransparencyExpense {
  title: string
  amount: number
  category: string
  status: ExpenseStatus
  payout_reference: string | null
  paid_out_at: string | null
}

export interface TransparencyReport {
  id: number
  title: string
  description: string | null
  target_amount: number | null
  amount_collected: number
  paid_count: number
  pending_count: number
  waived_count: number
  budget_allocation: Record<string, number> | null
  expenses: TransparencyExpense[]
  reserved_account?: ReservedAccount | null
}

// ── Public (guest) types ──────────────────────────────────────────────────────

export interface PublicCollection {
  id: number
  title: string
  description: string | null
  community_name: string
  amount_per_member: number
  target_amount: number | null
  amount_collected: number
  deadline: string | null
  status: CollectionStatus
  custom_fields: CustomFieldDef[] | null
}

export interface PublicPayment {
  payment_reference: string
  status: PaymentStatus
  amount: number
  paid_at: string | null
  custom_fields: CustomFieldDef[] | null
  form_submitted: boolean
}

export interface FormResponse {
  payment_id: number
  entry_id: number | null
  display_name: string
  amount: number
  paid_at: string | null
  submitted_at: string | null
  values: Record<string, string | boolean>
}

export interface CollectionResponses {
  custom_fields: CustomFieldDef[]
  responses: FormResponse[]
}

export interface ApiError {
  detail: string
}
