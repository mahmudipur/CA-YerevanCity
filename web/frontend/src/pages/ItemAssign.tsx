import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Spinner } from '../components/common/Spinner'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { PageTransition } from '../components/common/PageTransition'
import { ProgressBar } from '../components/wizard/ProgressBar'
import { ParticipantChecklist } from '../components/wizard/ParticipantChecklist'
import { SplitModeTabs } from '../components/wizard/SplitModeTabs'
import { ValueInputList } from '../components/wizard/ValueInputList'
import { ItemResultCallout } from '../components/wizard/ItemResultCallout'
import { sessionsApi } from '../api/endpoints'
import { ApiError } from '../api/client'
import type { AssignResult, SplitMode } from '../api/types'

export function ItemAssign() {
  const { sessionId = '', index = '0' } = useParams()
  const idx = Number(index)
  const navigate = useNavigate()
  const location = useLocation()
  const qc = useQueryClient()
  const returnToReview = new URLSearchParams(location.search).get('from') === 'review'

  const { data, isLoading } = useQuery({
    queryKey: ['item', sessionId, idx],
    queryFn: () => sessionsApi.getItem(sessionId, idx),
  })

  const [selected, setSelected] = useState<string[]>([])
  const [mode, setMode] = useState<SplitMode>('equal')
  const [values, setValues] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AssignResult | null>(null)

  useEffect(() => {
    if (!data) return
    setError(null)
    setResult(null)
    if (data.current_assignment) {
      const weights = data.current_assignment.assignment_weights
      const sharing = data.participants.filter((p) => (weights[p] ?? 0) !== 0 || data.current_assignment!.assignments[p] > 0)
      setSelected(sharing.length ? sharing : data.participants)
      const m = data.current_assignment.split_method
      setMode(m === 'percentage' ? 'percentage' : m === 'fixed' ? 'amount' : m === 'ratio' ? 'part' : 'equal')
      setValues(
        Object.fromEntries(
          data.participants.map((p) => [p, weights[p] ? String(weights[p]) : '']),
        ),
      )
    } else {
      setSelected(data.participants)
      setMode('equal')
      setValues({})
    }
  }, [data])

  const assign = useMutation({
    mutationFn: () => {
      const numericValues: Record<string, number> = {}
      for (const p of selected) {
        const raw = values[p]
        if (raw !== undefined && raw !== '') numericValues[p] = Number(raw)
      }
      return sessionsApi.assignItem(sessionId, idx, { mode, selected, values: numericValues })
    },
    onSuccess: (res) => {
      setError(null)
      setResult(res.result)
      qc.invalidateQueries({ queryKey: ['session', sessionId] })
      window.setTimeout(() => {
        if (returnToReview) {
          navigate(`/sessions/${sessionId}/review`)
        } else if (res.next_index !== null) {
          navigate(`/sessions/${sessionId}/items/${res.next_index}`)
        } else {
          navigate(`/sessions/${sessionId}/review`)
        }
      }, 550)
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not save this split.'),
  })

  if (isLoading || !data) {
    return (
      <Shell title="Split item" onBack={() => navigate(-1)}>
        <Spinner />
      </Shell>
    )
  }

  const { item, total } = data

  return (
    <Shell
      title="Split item"
      onBack={() => (returnToReview ? navigate(`/sessions/${sessionId}/review`) : navigate(-1))}
    >
      <PageTransition>
        <ProgressBar index={idx} total={total} />
        <Card>
          <ErrorBanner message={error} />
          <div className="mb-4 flex items-center gap-3">
            {item.image ? (
              <img
                src={item.image}
                alt=""
                aria-hidden="true"
                loading="lazy"
                className="h-16 w-16 shrink-0 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-muted)] object-contain p-1"
                onError={(e) => {
                  ;(e.currentTarget as HTMLImageElement).style.display = 'none'
                }}
              />
            ) : null}
            <div className="min-w-0">
              <div className="font-display text-lg leading-snug">{item.name}</div>
              <div className="font-mono-num text-sm text-text-muted">Net: {item.net_price.toLocaleString()} AMD</div>
            </div>
          </div>

          <div className="mb-4">
            <ParticipantChecklist participants={data.participants} selected={selected} onChange={setSelected} />
          </div>

          <SplitModeTabs value={mode} onChange={setMode} />
          <ValueInputList mode={mode} selected={selected} values={values} onChange={(name, raw) => setValues((v) => ({ ...v, [name]: raw }))} />

          {result && <ItemResultCallout result={result} />}

          <Button
            fullWidth
            className="mt-4"
            loading={assign.isPending}
            disabled={selected.length === 0}
            onClick={() => assign.mutate()}
          >
            {idx + 1 >= total && !returnToReview ? 'Save & review' : 'Save & continue'}
          </Button>
        </Card>
      </PageTransition>
    </Shell>
  )
}
