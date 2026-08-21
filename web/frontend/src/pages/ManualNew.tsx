import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { PageTransition } from '../components/common/PageTransition'
import { sessionsApi } from '../api/endpoints'
import { ApiError } from '../api/client'

export function ManualNew() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const via = searchParams.get('via') === 'ai' ? 'ai' : 'manual'
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  const create = useMutation({
    mutationFn: () => sessionsApi.create({ kind: 'manual', session_name: name.trim() || 'manual' }),
    onSuccess: (session) => navigate(`/sessions/${session.session_id}/roster?via=${via}`),
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not start session.'),
  })

  return (
    <Shell title="Manual expense" onBack={() => navigate(-1)}>
      <PageTransition>
        <Card>
          <ErrorBanner message={error} />
          <form
            onSubmit={(e) => {
              e.preventDefault()
              create.mutate()
            }}
            className="space-y-3"
          >
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-text-muted">Session name</span>
              <input
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Kavkaz restaurant"
                className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 outline-none"
              />
            </label>
            <Button type="submit" fullWidth loading={create.isPending}>
              Continue
            </Button>
          </form>
        </Card>
      </PageTransition>
    </Shell>
  )
}
