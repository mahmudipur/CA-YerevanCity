import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { UserGroupIcon } from '@heroicons/react/24/outline'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Spinner } from '../components/common/Spinner'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { PageTransition } from '../components/common/PageTransition'
import { sessionsApi } from '../api/endpoints'
import { ApiError } from '../api/client'

export function Roster() {
  const { sessionId = '' } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const via = searchParams.get('via') === 'ai' ? 'ai' : 'manual'
  const [temp, setTemp] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: session, isLoading } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => sessionsApi.get(sessionId),
  })

  const confirmRoster = useMutation({
    mutationFn: () => {
      const tempList = temp.split(',').map((s) => s.trim()).filter(Boolean)
      return sessionsApi.setRoster(sessionId, tempList)
    },
    onSuccess: (updated) => {
      setError(null)
      if (updated.kind === 'manual') {
        navigate(`/sessions/${sessionId}/${via === 'ai' ? 'receipt-import' : 'manual-items'}`)
      } else {
        navigate(`/sessions/${sessionId}/items/0`)
      }
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not set roster.'),
  })

  if (isLoading || !session) {
    return (
      <Shell title="Roster" onBack={() => navigate(-1)}>
        <Spinner />
      </Shell>
    )
  }

  const order = session.order
  const activeItems = session.items.filter((it) => !it.is_canceled)

  return (
    <Shell title="Roster" subtitle={order ? order.order_id : session.session_name ?? undefined} onBack={() => navigate(-1)}>
      <PageTransition>
        {order && (
          <Card className="mb-4">
            <div className="mb-1 flex items-center justify-between">
              <span className="font-display text-base">{order.order_id}</span>
              <span className="text-xs text-text-muted">{order.status_label}</span>
            </div>
            <div className="text-sm text-text-muted">{activeItems.length} active items</div>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
              {order.delivery_fee > 0 && <span>Delivery {order.delivery_fee.toLocaleString()}</span>}
              {order.service_fee > 0 && <span>Service {order.service_fee.toLocaleString()}</span>}
              {order.driver_tip > 0 && <span>Tip {order.driver_tip.toLocaleString()}</span>}
            </div>
            <div className="mt-2 flex items-baseline justify-between border-t border-[var(--color-border)] pt-2">
              <span className="text-sm text-text-muted">Total</span>
              <span className="font-mono-num text-lg font-semibold">{order.total_to_pay.toLocaleString()} AMD</span>
            </div>
          </Card>
        )}

        <Card>
          <ErrorBanner message={error} />
          <div className="mb-3 flex items-center gap-2">
            <UserGroupIcon className="h-5 w-5 text-primary" />
            <span className="font-medium">Participants</span>
          </div>
          <div className="mb-3 flex flex-wrap gap-1.5">
            {session.participants.map((p) => (
              <span key={p} className="rounded-full bg-primary/10 px-3 py-1 text-sm text-primary">
                {p}
              </span>
            ))}
          </div>
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-text-muted">
              Temporary participants for this session
            </span>
            <input
              value={temp}
              onChange={(e) => setTemp(e.target.value)}
              placeholder="comma-separated, e.g. Alex, Nairi"
              className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 outline-none"
            />
          </label>
          <Button fullWidth className="mt-4" loading={confirmRoster.isPending} onClick={() => confirmRoster.mutate()}>
            Continue
          </Button>
        </Card>
      </PageTransition>
    </Shell>
  )
}
