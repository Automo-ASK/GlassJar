import type {
  TokenResponse, User, Community, CommunityMember, CommunityLookup, Collection,
  CollectionDetail, CollectionMemberEntry,
  CommunityDashboard, Expense, LedgerResponse, TransparencyReport,
  MemberRole, ManualChannel, ActiveCollectionSummary, ReservedAccount,
  PublicCollection, PublicPayment, CustomFieldDef, CollectionResponses,
  Bank, AccountLookup,
} from './types'

const BASE_URL =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.PROD ? 'https://acafund-6auo.onrender.com' : 'http://localhost:8000')

// ── Token helpers ─────────────────────────────────────────────────────────────

function getToken(): string | null {
  return localStorage.getItem('acafund_token')
}

export function setToken(t: string) {
  localStorage.setItem('acafund_token', t)
}

function clearToken() {
  localStorage.removeItem('acafund_token')
}

export function hasToken(): boolean {
  return Boolean(getToken())
}

export async function logout() {
  // Best-effort server-side revocation; clear locally regardless of outcome.
  try {
    await req<void>('/auth/logout', { method: 'POST' })
  } catch {
    // offline or already-invalid token — the local clear below is what matters
  }
  clearToken()
}

// ── Core fetch ────────────────────────────────────────────────────────────────

async function req<T>(
  path: string,
  options: RequestInit = {},
  skipAuth = false,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    // Free-tier ngrok shows an HTML interstitial to browser-like requests
    // unless this is set — harmless no-op against a non-ngrok backend.
    'ngrok-skip-browser-warning': 'true',
    ...(options.headers as Record<string, string>),
  }
  if (!skipAuth) {
    const token = getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  if (res.status === 401 && !skipAuth) {
    clearToken()
    window.location.href = '/login'
    throw new Error('Unauthorised')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(body.detail ?? 'Request failed')
  }
  if (res.status === 204) return undefined as unknown as T
  return res.json() as Promise<T>
}

// When the backend is unreachable, req() throws a TypeError ("Failed to fetch").
// Read-only calls catch that specifically and return offline stand-in data so
// the UI can navigate; mutating calls surface the error.
function isOffline(e: unknown): boolean {
  return e instanceof TypeError
}

// ── Offline stand-in data ─────────────────────────────────────────────────────

const OFFLINE_USER: User = { id: 1, full_name: 'You', email: '' }

const OFFLINE_COMMUNITY = (overrides: Partial<Community> = {}): Community => ({
  id: 1, name: 'My Community', description: null,
  invite_code: 'INVITE-001', created_by: 1, ...overrides,
})

const OFFLINE_MEMBER = (id = 1, role: MemberRole = 'admin'): CommunityMember => ({
  id, community_id: 1, user_id: id, display_name: 'You',
  role, is_claimed: true,
})

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function register(full_name: string, email: string, password: string): Promise<TokenResponse> {
  const data = await req<TokenResponse>('/auth/register', {
    method: 'POST', body: JSON.stringify({ full_name, email, password }),
  }, true)
  setToken(data.access_token)
  return data
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const data = await req<TokenResponse>('/auth/login', {
    method: 'POST', body: JSON.stringify({ email, password }),
  }, true)
  setToken(data.access_token)
  return data
}

export async function getMe(): Promise<User> {
  try {
    return await req<User>('/auth/me')
  } catch (e) {
    if (!isOffline(e)) throw e
    return OFFLINE_USER
  }
}

// ── Communities ───────────────────────────────────────────────────────────────

export async function getMyCommunities(): Promise<Community[]> {
  try {
    return await req<Community[]>('/users/me/communities')
  } catch (e) {
    if (!isOffline(e)) throw e
    return []
  }
}

export async function createCommunity(name: string, description: string): Promise<Community> {
  return req<Community>('/communities', {
    method: 'POST', body: JSON.stringify({ name, description }),
  })
}

export async function lookupCommunity(invite_code: string): Promise<CommunityLookup> {
  return req<CommunityLookup>(`/communities/lookup?invite_code=${encodeURIComponent(invite_code)}`)
}

export async function joinCommunity(invite_code: string, claim_member_id?: number): Promise<CommunityMember> {
  return req<CommunityMember>('/communities/join', {
    method: 'POST', body: JSON.stringify({ invite_code, claim_member_id: claim_member_id ?? null }),
  })
}

export async function getCommunity(id: number): Promise<Community> {
  try {
    return await req<Community>(`/communities/${id}`)
  } catch (e) {
    if (!isOffline(e)) throw e
    return OFFLINE_COMMUNITY({ id })
  }
}

export async function getCommunityDashboard(id: number): Promise<CommunityDashboard> {
  try {
    return await req<CommunityDashboard>(`/communities/${id}/dashboard`)
  } catch (e) {
    if (!isOffline(e)) throw e
    return { treasury_balance: 0, active_collections: [] as ActiveCollectionSummary[], pending_expenses_count: 0, recent_ledger: [] }
  }
}

// ── Roster ────────────────────────────────────────────────────────────────────

export async function getMembers(communityId: number): Promise<CommunityMember[]> {
  try {
    return await req<CommunityMember[]>(`/communities/${communityId}/members`)
  } catch (e) {
    if (!isOffline(e)) throw e
    return [OFFLINE_MEMBER(1, 'admin')]
  }
}

export async function addMember(
  communityId: number,
  data: { display_name: string; email?: string; phone?: string },
): Promise<CommunityMember> {
  return req<CommunityMember>(`/communities/${communityId}/members`, {
    method: 'POST', body: JSON.stringify(data),
  })
}

export async function addMembersBulk(communityId: number, names: string[]): Promise<CommunityMember[]> {
  return req<CommunityMember[]>(`/communities/${communityId}/members/bulk`, {
    method: 'POST',
    body: JSON.stringify({ members: names.map((display_name) => ({ display_name })) }),
  })
}

export async function changeMemberRole(communityId: number, memberId: number, role: MemberRole): Promise<CommunityMember> {
  return req<CommunityMember>(`/communities/${communityId}/members/${memberId}/role`, {
    method: 'PATCH', body: JSON.stringify({ role }),
  })
}

export async function removeMember(communityId: number, memberId: number): Promise<void> {
  return req<void>(`/communities/${communityId}/members/${memberId}`, { method: 'DELETE' })
}

// ── Collections ───────────────────────────────────────────────────────────────

export async function getCollections(communityId: number): Promise<Collection[]> {
  try {
    return await req<Collection[]>(`/communities/${communityId}/collections`)
  } catch (e) {
    if (!isOffline(e)) throw e
    return []
  }
}

export async function createCollection(
  communityId: number,
  data: {
    title: string
    description?: string
    amount_per_member: number
    deadline?: string
    budget_allocation?: Record<string, number>
    custom_fields?: CustomFieldDef[]
  },
): Promise<Collection> {
  return req<Collection>(`/communities/${communityId}/collections`, {
    method: 'POST', body: JSON.stringify(data),
  })
}

export async function getCollection(id: number): Promise<CollectionDetail> {
  return req<CollectionDetail>(`/collections/${id}`)
}

export async function getMyPayment(collectionId: number): Promise<CollectionMemberEntry> {
  return req<CollectionMemberEntry>(`/collections/${collectionId}/payments/me`)
}

export async function closeCollection(id: number): Promise<Collection> {
  return req<Collection>(`/collections/${id}/close`, { method: 'PATCH' })
}

export async function syncCollectionEntries(id: number): Promise<{ added: number }> {
  return req<{ added: number }>(`/collections/${id}/entries/sync`, { method: 'POST' })
}

export async function getCollectionResponses(id: number): Promise<CollectionResponses> {
  return req<CollectionResponses>(`/collections/${id}/responses`)
}

// ── Entry actions (manual marking) ────────────────────────────────────────────

export async function markEntryPaid(
  collectionId: number, entryId: number, channel: ManualChannel, note?: string,
): Promise<CollectionMemberEntry> {
  return req<CollectionMemberEntry>(`/collections/${collectionId}/entries/${entryId}/mark-paid`, {
    method: 'POST', body: JSON.stringify({ channel, note: note ?? null }),
  })
}

export async function waiveEntry(collectionId: number, entryId: number, note?: string): Promise<CollectionMemberEntry> {
  return req<CollectionMemberEntry>(`/collections/${collectionId}/entries/${entryId}/waive`, {
    method: 'POST', body: JSON.stringify({ note: note ?? null }),
  })
}

export async function revertEntry(collectionId: number, entryId: number, note?: string): Promise<CollectionMemberEntry> {
  return req<CollectionMemberEntry>(`/collections/${collectionId}/entries/${entryId}/revert`, {
    method: 'POST', body: JSON.stringify({ note: note ?? null }),
  })
}

// ── Payments ──────────────────────────────────────────────────────────────────

export async function initiatePayment(collectionId: number): Promise<{ checkout_url: string; payment_reference: string }> {
  const redirect_url = `${window.location.origin}/payment-return?collection_id=${collectionId}`
  return req(`/collections/${collectionId}/pay`, {
    method: 'POST', body: JSON.stringify({ redirect_url }),
  })
}

// ── Public (guest) endpoints — no auth ────────────────────────────────────────

export async function getPublicCollection(shareToken: string): Promise<PublicCollection> {
  return req<PublicCollection>(`/public/collections/${shareToken}`, {}, true)
}

export async function publicPay(
  shareToken: string, payerEmail?: string,
): Promise<{ checkout_url: string; payment_reference: string }> {
  const redirect_url = `${window.location.origin}/payment-return?pay_token=${shareToken}`
  return req(`/public/collections/${shareToken}/pay`, {
    method: 'POST',
    body: JSON.stringify({ redirect_url, payer_email: payerEmail || null }),
  }, true)
}

export async function getPublicPayment(reference: string): Promise<PublicPayment> {
  return req<PublicPayment>(`/public/payments/${reference}`, {}, true)
}

export async function syncPublicPayment(reference: string): Promise<PublicPayment> {
  return req<PublicPayment>(`/public/payments/${reference}/sync`, { method: 'POST' }, true)
}

export async function submitPaymentForm(
  reference: string, values: Record<string, string | boolean>,
): Promise<PublicPayment> {
  return req<PublicPayment>(`/public/payments/${reference}/form`, {
    method: 'POST', body: JSON.stringify({ values }),
  }, true)
}

export async function getTransparencyReport(collectionId: number): Promise<TransparencyReport> {
  return req<TransparencyReport>(`/collections/${collectionId}/transparency`, {}, true)
}

// ── Expenses ──────────────────────────────────────────────────────────────────

export async function getExpenses(communityId: number): Promise<Expense[]> {
  try {
    return await req<Expense[]>(`/communities/${communityId}/expenses`)
  } catch (e) {
    if (!isOffline(e)) throw e
    return []
  }
}

export async function createExpense(
  communityId: number,
  data: {
    title: string
    amount: number
    category: string
    receipt_url?: string
    collection_id?: number
    destination_bank_name: string
    destination_bank_code: string
    destination_account_number: string
    destination_account_name: string
  },
): Promise<Expense> {
  return req<Expense>(`/communities/${communityId}/expenses`, {
    method: 'POST', body: JSON.stringify(data),
  })
}

export async function retryExpensePayout(expenseId: number): Promise<Expense> {
  return req<Expense>(`/expenses/${expenseId}/retry-payout`, { method: 'POST' })
}

export async function authorizeExpensePayout(expenseId: number, otp: string): Promise<Expense> {
  return req<Expense>(`/expenses/${expenseId}/authorize-payout`, {
    method: 'POST', body: JSON.stringify({ otp }),
  })
}

export async function resendExpenseOtp(expenseId: number): Promise<void> {
  return req<void>(`/expenses/${expenseId}/resend-otp`, { method: 'POST' })
}

export async function markExpensePaidManually(expenseId: number, payout_reference: string): Promise<Expense> {
  return req<Expense>(`/expenses/${expenseId}/mark-paid-manually`, {
    method: 'POST', body: JSON.stringify({ payout_reference }),
  })
}

// ── Bank lookups (for expense payouts) ────────────────────────────────────────

export async function getBanks(): Promise<Bank[]> {
  return req<Bank[]>('/meta/banks')
}

export async function resolveAccount(accountNumber: string, bankCode: string): Promise<AccountLookup> {
  const params = new URLSearchParams({ account_number: accountNumber, bank_code: bankCode })
  return req<AccountLookup>(`/meta/banks/resolve?${params.toString()}`)
}

// ── Reserved accounts ─────────────────────────────────────────────────────────

export async function getReservedAccount(communityId: number): Promise<ReservedAccount | null> {
  try {
    return await req<ReservedAccount | null>(`/communities/${communityId}/reserved-account`)
  } catch {
    // Never crash the dashboard over a missing reserved account
    return null
  }
}

export async function setupReservedAccount(communityId: number): Promise<ReservedAccount> {
  return req<ReservedAccount>(`/communities/${communityId}/reserved-account`, {
    method: 'POST',
  })
}

// ── Ledger ────────────────────────────────────────────────────────────────────

export async function getLedger(communityId: number): Promise<LedgerResponse> {
  try {
    return await req<LedgerResponse>(`/communities/${communityId}/ledger`)
  } catch (e) {
    if (!isOffline(e)) throw e
    return { entries: [], balance: 0, total: 0 }
  }
}

// ── AI Assistant ──────────────────────────────────────────────────────────────

export async function askAssistant(communityId: number, question: string): Promise<{ answer: string }> {
  return req<{ answer: string }>(`/communities/${communityId}/assistant/ask`, {
    method: 'POST', body: JSON.stringify({ question }),
  })
}
