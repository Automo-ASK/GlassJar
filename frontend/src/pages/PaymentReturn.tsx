import { useEffect, useState, useRef, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { CheckCircle, AlertTriangle, Copy, Check, Building2, RefreshCw } from 'lucide-react'
import Button from '../components/ui/Button'
import { getPublicPayment, submitPaymentForm } from '../lib/api'
import type { CustomFieldDef, PublicPayment } from '../lib/types'

function fmt(n: number) {
  return `₦${n.toLocaleString('en-NG')}`
}

const POLL_INTERVAL_MS = 5000
const POLL_ATTEMPTS_BEFORE_PENDING_MESSAGE = 24 // ~2 minutes
const POLL_ATTEMPTS_MAX = 360 // ~30 minutes, matching bank-transfer expectations

type Phase = 'loading' | 'transfer' | 'form' | 'confirming' | 'paid' | 'pending' | 'error'

export default function PaymentReturn() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const reference =
    searchParams.get('paymentReference') ??
    sessionStorage.getItem('acafund_payment_reference') ??
    ''
  const collectionId = Number(
    searchParams.get('collection_id') ?? sessionStorage.getItem('acafund_payment_collection_id')
  )
  const payToken =
    searchParams.get('pay_token') ?? sessionStorage.getItem('acafund_pay_token') ?? ''

  const [phase, setPhase] = useState<Phase>('loading')
  const [payment, setPayment] = useState<PublicPayment | null>(null)
  const [fields, setFields] = useState<CustomFieldDef[]>([])
  const [values, setValues] = useState<Record<string, string | boolean>>({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [copied, setCopied] = useState(false)
  const [checkingNow, setCheckingNow] = useState(false)
  const [hasCheckedOnce, setHasCheckedOnce] = useState(false)
  const pollRef = useRef<number | null>(null)
  const attemptsRef = useRef(0)

  const goBack = () => {
    if (collectionId) navigate(`/collections/${collectionId}`)
    else if (payToken) navigate(`/pay/${payToken}`)
    else navigate('/')
  }

  const handleConfirmed = useCallback((pay: PublicPayment) => {
    setPayment(pay)
    if (pollRef.current) clearInterval(pollRef.current)
    sessionStorage.removeItem('acafund_payment_reference')
    sessionStorage.removeItem('acafund_payment_collection_id')
    if (pay.custom_fields && pay.custom_fields.length > 0 && !pay.form_submitted) {
      setFields(pay.custom_fields)
      setPhase('form')
    } else {
      setPhase('paid')
    }
  }, [])

  const checkStatus = useCallback(async () => {
    if (!reference) return
    try {
      const pay = await getPublicPayment(reference)
      setPayment(pay)
      if (pay.status === 'paid') {
        handleConfirmed(pay)
      }
    } catch {
      // keep polling
    }
  }, [reference, handleConfirmed])

  const startPolling = useCallback(() => {
    attemptsRef.current = 0
    pollRef.current = window.setInterval(async () => {
      attemptsRef.current += 1
      await checkStatus()
      if (attemptsRef.current === POLL_ATTEMPTS_BEFORE_PENDING_MESSAGE) {
        setPhase((prev) => (prev === 'transfer' || prev === 'confirming' ? 'pending' : prev))
      }
      if (attemptsRef.current >= POLL_ATTEMPTS_MAX && pollRef.current) {
        clearInterval(pollRef.current)
      }
    }, POLL_INTERVAL_MS)
  }, [checkStatus])

  useEffect(() => {
    if (!reference) { setPhase('error'); return }

    let cancelled = false
    ;(async () => {
      try {
        const pay = await getPublicPayment(reference)
        if (cancelled) return
        setPayment(pay)
        if (pay.status === 'paid') {
          handleConfirmed(pay)
        } else if (pay.va_account_number) {
          setPhase('transfer')
          startPolling()
        } else {
          setPhase('confirming')
          startPolling()
        }
      } catch {
        if (!cancelled) { setPhase('confirming'); startPolling() }
      }
    })()

    return () => {
      cancelled = true
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [reference, startPolling, handleConfirmed])

  const handleCheckNow = async () => {
    setCheckingNow(true)
    setHasCheckedOnce(true)
    await checkStatus()
    setCheckingNow(false)
  }

  const copyAccountNumber = () => {
    if (!payment?.va_account_number) return
    navigator.clipboard.writeText(payment.va_account_number)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const updateValue = (key: string, value: string | boolean) =>
    setValues((prev) => ({ ...prev, [key]: value }))

  const handleFormSubmit = async () => {
    setFormError('')
    for (const field of fields) {
      const v = values[field.key]
      if (field.required && (v === undefined || v === '' || (v === false && field.type === 'checkbox'))) {
        setFormError(`${field.label} is required`)
        return
      }
    }
    setSubmitting(true)
    try {
      await submitPaymentForm(reference, values)
      setPhase('paid')
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : 'Could not submit form')
    } finally {
      setSubmitting(false)
    }
  }

  if (phase === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="w-14 h-14 border-4 border-black border-t-primary rounded-full animate-spin" />
      </div>
    )
  }

  if (phase === 'transfer' || phase === 'pending') {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 py-10">
        <div className="border-4 border-black neo-shadow-lg bg-white p-8 max-w-sm w-full">
          <div className="text-center mb-6">
            <Building2 size={32} className="mx-auto mb-3 text-primary" />
            <h1 className="text-[22px] font-bold mb-1">Transfer to Confirm Payment</h1>
            <p className="text-[13px] text-on-surface-variant">
              {phase === 'pending'
                ? "Still waiting on your transfer. If you've already sent it, this can take a few minutes to reflect — you can leave this page open or come back later."
                : 'Send exactly this amount to the account below. We’ll confirm automatically the moment it lands — no need to upload a screenshot.'}
            </p>
          </div>
          {payment && (
            <div className="border-2 border-black bg-surface-container p-4 flex flex-col gap-3 mb-4">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-on-surface-variant">Amount</p>
                <p className="text-[20px] font-bold text-primary">
                  {fmt(payment.va_amount ?? payment.amount)}
                </p>
                <p className="text-[11px] text-on-surface-variant mt-0.5">
                  Send this exact amount — a different amount will be rejected by the bank.
                </p>
              </div>
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-on-surface-variant">Bank</p>
                <p className="text-[15px] font-bold">{payment.va_bank_name}</p>
              </div>
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-on-surface-variant mb-1">Account Number</p>
                <div className="flex items-center gap-2">
                  <p className="text-[18px] font-bold tracking-[0.08em]">{payment.va_account_number}</p>
                  <button
                    onClick={copyAccountNumber}
                    className="border-2 border-black p-1.5 neo-shadow-sm neo-btn bg-white flex-shrink-0"
                    aria-label="Copy account number"
                  >
                    {copied ? <Check size={12} /> : <Copy size={12} />}
                  </button>
                </div>
              </div>
            </div>
          )}
          <div className="flex flex-col gap-2">
            {hasCheckedOnce ? (
              <div className="flex items-center justify-center gap-2 border-2 border-black bg-surface-container py-2.5 text-[13px] font-bold">
                <RefreshCw size={14} className="animate-spin" />
                Checking automatically…
              </div>
            ) : (
              <Button variant="primary" fullWidth loading={checkingNow} onClick={handleCheckNow}>
                <RefreshCw size={14} />
                I've Paid — Check Now
              </Button>
            )}
            <Button variant="white" fullWidth onClick={goBack}>
              {collectionId ? 'Back to Collection' : 'Back'}
            </Button>
          </div>
        </div>
      </div>
    )
  }

  if (phase === 'form') {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 py-10">
        <div className="border-4 border-black neo-shadow-lg bg-white p-8 max-w-sm w-full">
          <h1 className="text-[22px] font-bold mb-1">Almost done!</h1>
          <p className="text-[14px] text-on-surface-variant mb-6">
            Your payment is confirmed. Just a couple of details to wrap up.
          </p>
          <div className="flex flex-col gap-4">
            {fields.map((field) => (
              <div key={field.key} className="flex flex-col gap-1">
                <label htmlFor={field.key} className="text-[12px] font-bold uppercase tracking-[0.06em]">
                  {field.label} {field.required && <span className="text-error">*</span>}
                </label>
                {field.type === 'select' ? (
                  <select
                    id={field.key}
                    value={(values[field.key] as string) ?? ''}
                    onChange={(e) => updateValue(field.key, e.target.value)}
                    className="border-2 border-black px-3 py-2 text-[14px] bg-white focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="">Select…</option>
                    {(field.options ?? []).map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                ) : field.type === 'checkbox' ? (
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      id={field.key}
                      type="checkbox"
                      checked={Boolean(values[field.key])}
                      onChange={(e) => updateValue(field.key, e.target.checked)}
                      className="w-4 h-4 border-2 border-black accent-primary"
                    />
                    <span className="text-[13px]">Yes</span>
                  </label>
                ) : (
                  <input
                    id={field.key}
                    type={field.type === 'number' ? 'number' : field.type === 'email' ? 'email' : field.type === 'phone' ? 'tel' : 'text'}
                    value={(values[field.key] as string) ?? ''}
                    onChange={(e) => updateValue(field.key, e.target.value)}
                    className="border-2 border-black px-3 py-2 text-[14px] bg-white focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                )}
              </div>
            ))}
            {formError && <p className="text-[12px] text-error font-bold">{formError}</p>}
            <Button fullWidth size="lg" loading={submitting} onClick={handleFormSubmit}>
              Continue
            </Button>
          </div>
        </div>
      </div>
    )
  }

  if (phase === 'confirming') {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="border-4 border-black neo-shadow-lg bg-white p-10 max-w-sm w-full text-center">
          <div className="w-14 h-14 border-4 border-black border-t-primary rounded-full animate-spin mx-auto mb-6" />
          <h1 className="text-[22px] font-bold mb-2">Confirming Payment</h1>
          <p className="text-[14px] text-on-surface-variant">
            We're verifying your payment. This usually takes a few seconds…
          </p>
        </div>
      </div>
    )
  }

  if (phase === 'paid') {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="border-4 border-black neo-shadow-lg bg-primary-container p-10 max-w-sm w-full text-center">
          <CheckCircle size={48} className="mx-auto mb-4 text-primary" />
          <h1 className="text-[24px] font-bold mb-2">Payment Confirmed!</h1>
          <p className="text-[14px] text-on-primary-container/80 mb-8">
            Your dues have been received and recorded. Thank you!
          </p>
          <Button variant="black" fullWidth onClick={goBack}>
            {collectionId ? 'Back to Collection' : payToken ? 'Back to Payment Page' : 'Done'}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="border-4 border-black neo-shadow-lg bg-white p-10 max-w-sm w-full text-center">
        <AlertTriangle size={40} className="mx-auto mb-4 text-error" />
        <h1 className="text-[22px] font-bold mb-2">Something went wrong</h1>
        <p className="text-[14px] text-on-surface-variant mb-8">
          We couldn't verify your payment. Please check with your admin.
        </p>
        <Button variant="white" fullWidth onClick={goBack}>
          Go Back
        </Button>
      </div>
    </div>
  )
}
