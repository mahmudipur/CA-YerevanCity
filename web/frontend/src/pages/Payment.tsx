import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { BanknotesIcon, CreditCardIcon } from '@heroicons/react/24/outline'
import clsx from 'clsx'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { PageTransition } from '../components/common/PageTransition'
import { RevolutForm } from '../components/payment/RevolutForm'
import { paymentApi, sessionsApi } from '../api/endpoints'
import { ApiError } from '../api/client'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import type { Currency } from '../api/types'

export function Payment() {
  const { sessionId = '' } = useParams()
  const navigate = useNavigate()
  const [method, setMethod] = useState<'cash' | 'revolut'>('cash')
  const [rate, setRate] = useState('')
  const [eurPaid, setEurPaid] = useState('')
  const [isWeekend, setIsWeekend] = useState(false)
  const [isFairUsage, setIsFairUsage] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<Currency | null>(null)
  const [prefilled, setPrefilled] = useState(false)

  // When editing a past split, seed the form from its already-saved payment info.
  const { data: existingSession } = useQuery({ queryKey: ['session', sessionId], queryFn: () => sessionsApi.get(sessionId) })
  useEffect(() => {
    if (prefilled || !existingSession?.currency) return
    const c = existingSession.currency
    setMethod(c.method)
    if (c.method === 'revolut') {
      setRate(String(c.rate))
      setEurPaid(String(c.eur_paid))
      setIsWeekend(c.is_weekend)
      setIsFairUsage(c.is_fair_usage)
      setPreview(c)
    }
    setPrefilled(true)
  }, [existingSession, prefilled])

  const debouncedRate = useDebouncedValue(rate, 350)
  const debouncedEur = useDebouncedValue(eurPaid, 350)

  const previewQuery = useQuery({
    queryKey: ['payment-preview', sessionId, debouncedRate, debouncedEur, isWeekend, isFairUsage],
    queryFn: () =>
      paymentApi.revolut(sessionId, {
        rate: Number(debouncedRate),
        eur_paid: Number(debouncedEur),
        is_weekend: isWeekend,
        is_fair_usage: isFairUsage,
      }),
    enabled: method === 'revolut' && Number(debouncedRate) > 0 && Number(debouncedEur) > 0,
    retry: false,
  })

  useEffect(() => {
    if (previewQuery.data) setPreview(previewQuery.data as Currency)
  }, [previewQuery.data])

  const confirm = useMutation({
    mutationFn: () => {
      if (method === 'cash') return paymentApi.cash(sessionId)
      return paymentApi.revolut(sessionId, {
        rate: Number(rate),
        eur_paid: Number(eurPaid),
        is_weekend: isWeekend,
        is_fair_usage: isFairUsage,
      })
    },
    onSuccess: () => navigate(`/sessions/${sessionId}/done`),
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not save payment info.'),
  })

  return (
    <Shell title="Payment" onBack={() => navigate(-1)}>
      <PageTransition>
        <ErrorBanner message={error} />
        <div className="mb-4 flex gap-2">
          {(
            [
              { key: 'cash', label: 'Cash', icon: BanknotesIcon },
              { key: 'revolut', label: 'Revolut', icon: CreditCardIcon },
            ] as const
          ).map((m) => (
            <button
              key={m.key}
              type="button"
              onClick={() => setMethod(m.key)}
              className={clsx(
                'flex min-h-11 flex-1 cursor-pointer items-center justify-center gap-2 rounded-xl border py-3 text-sm font-semibold transition-colors',
                method === m.key
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-[var(--color-border)] text-text-muted hover:bg-[var(--color-surface-muted)]',
              )}
            >
              <m.icon className="h-4 w-4" />
              {m.label}
            </button>
          ))}
        </div>

        <Card>
          {method === 'cash' ? (
            <p className="text-sm text-text-muted">No exchange info needed — everyone settles in AMD.</p>
          ) : (
            <RevolutForm
              rate={rate}
              eurPaid={eurPaid}
              isWeekend={isWeekend}
              isFairUsage={isFairUsage}
              onChange={(patch) => {
                if (patch.rate !== undefined) setRate(patch.rate)
                if (patch.eurPaid !== undefined) setEurPaid(patch.eurPaid)
                if (patch.isWeekend !== undefined) setIsWeekend(patch.isWeekend)
                if (patch.isFairUsage !== undefined) setIsFairUsage(patch.isFairUsage)
              }}
              preview={preview}
              previewLoading={previewQuery.isFetching}
            />
          )}

          <Button
            fullWidth
            className="mt-4"
            loading={confirm.isPending}
            disabled={method === 'revolut' && (!Number(rate) || !Number(eurPaid))}
            onClick={() => confirm.mutate()}
          >
            Confirm & save
          </Button>
        </Card>
      </PageTransition>
    </Shell>
  )
}
