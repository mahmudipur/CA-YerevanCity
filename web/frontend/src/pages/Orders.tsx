import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ArrowPathIcon, ArrowRightOnRectangleIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { Spinner } from '../components/common/Spinner'
import { PageTransition } from '../components/common/PageTransition'
import { authApi, ordersApi, sessionsApi } from '../api/endpoints'
import { ApiError } from '../api/client'

export function Orders() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [orderId, setOrderId] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: authStatus, isLoading: authLoading } = useQuery({
    queryKey: ['auth-status'],
    queryFn: authApi.status,
  })

  const logout = useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['auth-status'] }),
  })

  const { data: recent, isLoading: listLoading } = useQuery({
    queryKey: ['orders-list'],
    queryFn: () => ordersApi.list(1, 10),
    enabled: authStatus?.authenticated === true,
    retry: false,
  })

  const startSession = useMutation({
    mutationFn: async (id: string) => {
      const order = id ? await ordersApi.fetch(id) : await ordersApi.latest()
      return sessionsApi.create({ kind: 'yc', order_id: order.order_id })
    },
    onSuccess: (session) => {
      setError(null)
      navigate(`/sessions/${session.session_id}/roster`)
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not fetch that order.'),
  })

  if (authLoading) {
    return (
      <Shell title="Yerevan City order" onBack={() => navigate(-1)}>
        <Spinner />
      </Shell>
    )
  }

  if (authStatus && !authStatus.authenticated) {
    return (
      <Shell title="Yerevan City order" onBack={() => navigate(-1)}>
        <PageTransition>
          <Card className="text-center">
            <p className="mb-3 text-sm text-text-muted">Sign in to fetch your orders.</p>
            <Button onClick={() => navigate('/login')}>Sign in</Button>
          </Card>
        </PageTransition>
      </Shell>
    )
  }

  return (
    <Shell title="Yerevan City order" onBack={() => navigate(-1)}>
      <PageTransition>
        <ErrorBanner message={error} />

        {authStatus?.phone_e164 && (
          <div className="mb-4 flex items-center justify-between text-xs text-text-muted">
            <span>Signed in as {authStatus.phone_e164}</span>
            <button
              type="button"
              onClick={() => logout.mutate()}
              disabled={logout.isPending}
              className="flex cursor-pointer items-center gap-1 text-accent hover:underline disabled:opacity-50"
            >
              <ArrowRightOnRectangleIcon className="h-3.5 w-3.5" />
              Sign out
            </button>
          </div>
        )}

        <Card className="mb-4">
          <label className="mb-1.5 block text-sm font-medium text-text-muted">Order ID (leave blank for latest)</label>
          <div className="flex gap-2">
            <div className="flex flex-1 items-center gap-2 rounded-xl border border-[var(--color-border)] px-3.5 py-2.5">
              <MagnifyingGlassIcon className="h-4 w-4 text-text-muted" />
              <input
                value={orderId}
                onChange={(e) => setOrderId(e.target.value)}
                placeholder="KM0030169110"
                className="min-h-11 w-full bg-transparent outline-none"
              />
            </div>
          </div>
          <Button
            fullWidth
            className="mt-3"
            icon={<ArrowPathIcon className="h-4 w-4" />}
            loading={startSession.isPending}
            onClick={() => startSession.mutate(orderId.trim())}
          >
            {orderId.trim() ? 'Fetch order' : 'Use latest order'}
          </Button>
        </Card>

        {listLoading && <Spinner label="Loading recent orders…" />}

        {recent && recent.length > 0 && (
          <>
            <div className="mb-2 text-sm font-medium text-text-muted">Recent orders</div>
            <ul className="space-y-2">
              {recent.map((o) => (
                <li key={o.order_id}>
                  <button
                    type="button"
                    onClick={() => startSession.mutate(o.order_id)}
                    className="flex w-full min-h-11 cursor-pointer items-center justify-between rounded-xl border border-[var(--color-border)] bg-surface px-3.5 py-3 text-left transition-colors hover:bg-[var(--color-surface-muted)]"
                  >
                    <div>
                      <div className="font-medium">{o.order_id}</div>
                      <div className="text-xs text-text-muted">{o.create_date?.slice(0, 10)}</div>
                    </div>
                    <div className="font-mono-num text-sm font-semibold">{o.total_to_pay.toLocaleString()} AMD</div>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </PageTransition>
    </Shell>
  )
}
