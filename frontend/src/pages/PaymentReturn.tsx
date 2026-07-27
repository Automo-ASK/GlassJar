import { useEffect, useState, useRef, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { CheckCircle, AlertTriangle, RefreshCw } from 'lucide-react'
import Button from '../components/ui/Button'
import { getPublicPayment, syncPublicPayment, submitPaymentForm } from '../lib/api'
import type { CustomFieldDef } from '../lib/types'

export default function PaymentReturn() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  // Monnify can corrupt query params on redirect — sessionStorage is the
  // reliable source. Works for both logged-in members and guests because the
  // status endpoints are public, keyed by payment reference.
  const reference =
    searchParams.get('paymentReference') ??
    sessionStorage.getItem('acafund_payment_reference') ??
    ''
  const collectionId = Number(
    searchParams.get('collection_id') ?? sessionStorage.getItem('acafund_payment_collection_id')
  )
  const payToken =
    searchParams.get('pay_token') ?? sessionStorage.getItem('acafund_pay_token') ?? ''

  const [phase, setPhase] = useState<'loading' | 'form' | 'confirming' | 'paid' | 'pending' | 'error'>('loading')
  const [fields, setFields] = useState<CustomFieldDef[]>([])
  const [values, setValues] = useState<Record<string, string | boolean>>({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const pollRef = useRef<number | null>(null)

  const goBack = () => {
    if (collectionId) navigate(`/collections/${collectionId}`)
    else if (payToken) navigate(`/pay/${payToken}`)
    else navigate('/')
  }

  const checkStatus = useCallback(async () => {
    if (!reference) { setPhase('error'); return }
    try {
      const pay = await getPublicPayment(reference)
      if (pay.status === 'paid') {
        setPhase('paid')
        sessionStorage.removeItem('acafund_payment_reference')
        sessionStorage.removeItem('acafund_payment_collection_id')
        if (pollRef.current) clearInterval(pollRef.current)
      }
    } catch {
      // keep polling
    }
  }, [reference])

  const startPolling = useCallback(() => {
    setPhase((prev) => (prev === 'paid' ? prev : 'confirming'))
    checkStatus()
    let count = 0
    pollRef.current = window.setInterval(async () => {
      count++
      await checkStatus()
      if (count >= 10) {
        if (pollRef.current) clearInterval(pollRef.current)
        setPhase((prev) => (prev === 'confirming' ? 'pending' : prev))
      }
    }, 2000)
  }, [checkStatus])

  useEffect(() => {
    if (!reference) { setPhase('error'); return }

    let cancelled = false
    ;(async () => {
      try {
        const pay = await getPublicPayment(reference)
        if (cancelled) return
        if (pay.custom_fields && pay.custom_fields.length > 0 && !pay.form_submitted) {
          setFields(pay.custom_fields)
          setPhase('form')
        } else if (pay.status === 'paid') {
          setPhase('paid')
          sessionStorage.removeItem('acafund_payment_reference')
          sessionStorage.removeItem('acafund_payment_collection_id')
        } else {
          startPolling()
        }
      } catch {
        if (!cancelled) startPolling()
      }
    })()

    return () => {
      cancelled = true
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [reference, startPolling])

  const updateValue = (key: string, value: string | boolean) =>
    setValues((prev) => ({ ...prev, [key]: value }))

  const handleFormSubmit = async () => {
    setFormError('')
    for (const field of fields) {
      const v = values[field.key]
      if (field.required && (v === undefined || v === '' || v === false && field.type === 'checkbox')) {
        setFormError(`${field.label} is required`)
        return
      }
    }
    setSubmitting(true)
    try {
      await submitPaymentForm(reference, values)
      startPolling()
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : 'Could not submit form')
    } finally {
      setSubmitting(false)
    }
  }

  const handleSync = async () => {
    if (!reference) return
    setSyncing(true)
    try {
      const pay = await syncPublicPayment(reference)
      if (pay.status === 'paid') {
        setPhase('paid')
        sessionStorage.removeItem('acafund_payment_reference')
        sessionStorage.removeItem('acafund_payment_collection_id')
      }
    } catch {
      // show current state
    } finally {
      setSyncing(false)
    }
  }

  if (phase === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="w-14 h-14 border-4 border-black border-t-primary rounded-full animate-spin" />
      </div>
    )
  }

  if (phase === 'form') {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 py-10">
        <div className="border-4 border-black neo-shadow-lg bg-white p-8 max-w-sm w-full">
          <h1 className="text-[22px] font-bold mb-1">Almost done!</h1>
          <p className="text-[14px] text-on-surface-variant mb-6">
            Your payment went through. Just a couple of details before we confirm it.
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
            We're verifying your payment with the bank. This usually takes a few seconds…
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

  if (phase === 'pending') {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="border-4 border-black neo-shadow-lg bg-white p-10 max-w-sm w-full text-center">
          <AlertTriangle size={40} className="mx-auto mb-4 text-error" />
          <h1 className="text-[22px] font-bold mb-2">Still Processing</h1>
          <p className="text-[14px] text-on-surface-variant mb-8">
            Your payment is still being processed. If you've completed checkout, it may take a little longer to reflect.
          </p>
          <div className="flex flex-col gap-3">
            <Button variant="primary" fullWidth loading={syncing} onClick={handleSync}>
              <RefreshCw size={14} />
              Sync Payment Status
            </Button>
            <Button variant="white" fullWidth onClick={goBack}>
              {collectionId ? 'Back to Collection' : 'Back'}
            </Button>
          </div>
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
