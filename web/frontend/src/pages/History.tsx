import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ArrowDownTrayIcon, PencilSquareIcon } from '@heroicons/react/24/outline'
import { Shell } from '../components/common/Shell'
import { Spinner } from '../components/common/Spinner'
import { Card } from '../components/common/Card'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { PageTransition } from '../components/common/PageTransition'
import { historyApi, csvDownloadUrl } from '../api/endpoints'
import { ApiError } from '../api/client'
import { useState } from 'react'

export function History() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const { data, isLoading } = useQuery({ queryKey: ['history'], queryFn: historyApi.list })

  const edit = useMutation({
    mutationFn: (id: string) => historyApi.edit(id),
    onSuccess: (session) => {
      setError(null)
      qc.setQueryData(['session', session.session_id], session)
      navigate(`/sessions/${session.session_id}/review`)
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not load that split for editing.'),
  })

  return (
    <Shell title="Past splits" onBack={() => navigate('/')}>
      <PageTransition>
        <ErrorBanner message={error} />
        {isLoading && <Spinner />}
        {data && data.length === 0 && (
          <Card className="text-center text-sm text-text-muted">No splits saved yet.</Card>
        )}
        <ul className="space-y-2">
          {data?.map((row) => (
            <li key={row.id}>
              <Card className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate font-medium">{row.session_name || row.id}</div>
                  <div className="text-xs text-text-muted">
                    {row.status_label} · {row.participants.join(', ')}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  {row.order_total != null && (
                    <span className="mr-1 font-mono-num text-sm font-semibold">{row.order_total.toLocaleString()} AMD</span>
                  )}
                  <button
                    type="button"
                    aria-label={`Edit ${row.id}`}
                    disabled={edit.isPending}
                    onClick={() => edit.mutate(row.id)}
                    className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-text-muted transition-colors hover:bg-[var(--color-surface-muted)] hover:text-primary disabled:opacity-50"
                  >
                    <PencilSquareIcon className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    aria-label={`Download CSV for ${row.id}`}
                    onClick={() => window.open(csvDownloadUrl(row.id), '_blank')}
                    className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-text-muted transition-colors hover:bg-[var(--color-surface-muted)] hover:text-primary"
                  >
                    <ArrowDownTrayIcon className="h-4 w-4" />
                  </button>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      </PageTransition>
    </Shell>
  )
}
