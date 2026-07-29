import { useState, useEffect, type FormEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { CheckCircle } from 'lucide-react'
import Input from '../components/ui/Input'
import Button from '../components/ui/Button'
import { createExpense, getBanks, resolveAccount } from '../lib/api'
import type { Bank } from '../lib/types'

const CATEGORIES = [
  'Food & Catering', 'Venue', 'Decoration', 'Printing', 'Transport',
  'Equipment', 'Gifts & Souvenirs', 'Photography', 'Entertainment', 'Other',
]

export default function CreateExpense() {
  const { id } = useParams<{ id: string }>()
  const communityId = Number(id)
  const navigate = useNavigate()

  const [title, setTitle] = useState('')
  const [amount, setAmount] = useState('')
  const [category, setCategory] = useState(CATEGORIES[0])
  const [receiptUrl, setReceiptUrl] = useState('')

  const [banks, setBanks] = useState<Bank[]>([])
  const [banksError, setBanksError] = useState('')
  const [bankCode, setBankCode] = useState('')
  const [accountNumber, setAccountNumber] = useState('')
  const [verifiedName, setVerifiedName] = useState('')
  const [verifying, setVerifying] = useState(false)
  const [verifyError, setVerifyError] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    getBanks()
      .then((b) => { setBanks(b); if (b.length) setBankCode(b[0].code) })
      .catch((e: unknown) => setBanksError(e instanceof Error ? e.message : 'Failed to load bank list'))
  }, [])

  const invalidateVerification = () => {
    if (verifiedName) setVerifiedName('')
    setVerifyError('')
  }

  // Auto-verify once a 10-digit account number and a bank are both set — no
  // button to click. Debounced, and guarded against stale responses if the
  // input changes mid-request.
  useEffect(() => {
    const trimmed = accountNumber.trim()
    if (!bankCode || !/^\d{10}$/.test(trimmed)) return

    let cancelled = false
    const timer = setTimeout(async () => {
      setVerifying(true)
      setVerifyError('')
      try {
        const result = await resolveAccount(trimmed, bankCode)
        if (!cancelled) setVerifiedName(result.account_name)
      } catch (e: unknown) {
        if (!cancelled) setVerifyError(e instanceof Error ? e.message : 'Could not resolve this account')
      } finally {
        if (!cancelled) setVerifying(false)
      }
    }, 400)

    return () => { cancelled = true; clearTimeout(timer) }
  }, [accountNumber, bankCode])

  const validate = () => {
    const e: Record<string, string> = {}
    if (!title.trim()) e.title = 'Title is required'
    const amt = parseFloat(amount)
    if (!amount || isNaN(amt) || amt <= 0) e.amount = 'Enter a valid amount'
    if (!verifiedName) e.account = 'Verify the destination account before paying'
    return e
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) { setFieldErrors(errs); return }
    setFieldErrors({}); setError('')
    setLoading(true)
    try {
      const bank = banks.find((b) => b.code === bankCode)
      const exp = await createExpense(communityId, {
        title: title.trim(),
        amount: parseFloat(amount),
        category,
        receipt_url: receiptUrl.trim() || undefined,
        destination_bank_name: bank?.name ?? '',
        destination_bank_code: bankCode,
        destination_account_number: accountNumber.trim(),
        destination_account_name: verifiedName,
      })
      navigate(`/expenses/${exp.id}?community=${communityId}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to submit expense')
    } finally { setLoading(false) }
  }

  return (
    <div className="max-w-lg mx-auto">
      <div className="mb-8">
        <h1 className="text-[28px] font-bold tracking-tight">Pay for Something</h1>
        <p className="text-[14px] text-on-surface-variant mt-1">
          Admin or treasurer only. The transfer goes out as soon as you confirm.
        </p>
      </div>

      {error && (
        <div className="mb-6 border-2 border-error bg-error-container p-3 text-[13px] font-bold text-error">{error}</div>
      )}

      <div className="border-4 border-black neo-shadow-lg bg-white p-8">
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <Input id="title" label="What's this for" placeholder="e.g. Venue booking deposit"
            value={title} onChange={(e) => setTitle(e.target.value)} error={fieldErrors.title} />

          <Input id="amount" label="Amount (₦)" type="number" min="1" step="0.01" placeholder="e.g. 50000"
            value={amount} onChange={(e) => setAmount(e.target.value)} error={fieldErrors.amount} />

          <div className="flex flex-col gap-1.5">
            <label htmlFor="category" className="text-[12px] font-bold uppercase tracking-[0.08em]">Category</label>
            <select
              id="category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="border-2 border-black bg-white px-4 py-3 text-[15px] font-sans focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          {/* Destination account — where the money goes, verified before paying */}
          <div className="border-2 border-black bg-surface-container p-4 flex flex-col gap-4">
            <p className="text-[12px] font-bold uppercase tracking-[0.08em]">Who Gets Paid</p>

            {banksError && <p className="text-[12px] text-error font-bold">{banksError}</p>}

            <div className="flex flex-col gap-1.5">
              <label htmlFor="bank" className="text-[12px] font-bold uppercase tracking-[0.08em]">Bank</label>
              <select
                id="bank"
                value={bankCode}
                onChange={(e) => { setBankCode(e.target.value); invalidateVerification() }}
                disabled={banks.length === 0}
                className="border-2 border-black bg-white px-4 py-3 text-[15px] font-sans focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
              >
                {banks.map((b) => <option key={b.code} value={b.code}>{b.name}</option>)}
              </select>
            </div>

            <Input id="accountNumber" label="Account Number" placeholder="10-digit account number"
              value={accountNumber}
              onChange={(e) => { setAccountNumber(e.target.value); invalidateVerification() }} />

            {verifying && (
              <p className="text-[12px] text-on-surface-variant">Looking up account name…</p>
            )}
            {verifyError && <p className="text-[12px] text-error font-bold">{verifyError}</p>}
            {verifiedName && (
              <div className="flex items-center gap-2 border-2 border-secondary bg-secondary-container/30 px-3 py-2">
                <CheckCircle size={14} className="text-secondary flex-shrink-0" />
                <p className="text-[13px] font-bold">{verifiedName}</p>
              </div>
            )}
            {fieldErrors.account && !verifiedName && (
              <p className="text-[12px] text-error font-bold">{fieldErrors.account}</p>
            )}
          </div>

          <Input id="receipt" label="Receipt URL (optional, stored in your drive)" type="url"
            placeholder="Paste Google Drive link..."
            value={receiptUrl} onChange={(e) => setReceiptUrl(e.target.value)} />

          <Button type="submit" loading={loading} fullWidth size="lg">
            {amount ? `Pay ₦${Number(amount).toLocaleString('en-NG')}` : 'Pay Now'}
          </Button>
        </form>
      </div>
    </div>
  )
}
