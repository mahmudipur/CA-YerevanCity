import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowUpTrayIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Spinner } from '../components/common/Spinner'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { PageTransition } from '../components/common/PageTransition'
import { CopyButton } from '../components/common/CopyButton'
import { receiptApi, sessionsApi } from '../api/endpoints'
import { ApiError } from '../api/client'

function extractItems(raw: string): { name: string; price: number; service?: number | string | null }[] {
  // Tolerate an AI wrapping the JSON in ```json fences despite instructions not to.
  const cleaned = raw.trim().replace(/^```(?:json)?/i, '').replace(/```$/, '').trim()
  let parsed: unknown
  try {
    parsed = JSON.parse(cleaned)
  } catch {
    throw new Error("That doesn't look like valid JSON. Paste exactly what the AI returned.")
  }
  const items = (parsed as { items?: unknown })?.items
  if (!Array.isArray(items) || items.length === 0) {
    throw new Error('No "items" array found in that JSON.')
  }
  return items
}

export function ReceiptImport() {
  const { sessionId = '' } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [pasted, setPasted] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: promptData, isLoading: promptLoading } = useQuery({
    queryKey: ['receipt-prompt'],
    queryFn: receiptApi.getPrompt,
  })

  const importMutation = useMutation({
    mutationFn: async () => {
      const items = extractItems(pasted)
      return sessionsApi.importItems(sessionId, items)
    },
    onSuccess: (updated) => {
      setError(null)
      qc.setQueryData(['session', sessionId], updated)
      navigate(`/sessions/${sessionId}/manual-items`)
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Could not import those items.'),
  })

  return (
    <Shell title="Scan with AI" onBack={() => navigate(-1)}>
      <PageTransition>
        <ErrorBanner message={error} />

        <Card className="mb-4">
          <div className="mb-3 flex items-center gap-2">
            <SparklesIcon className="h-5 w-5 text-primary" />
            <span className="font-medium">1. Send this prompt + a receipt photo to any AI</span>
          </div>
          {promptLoading ? (
            <Spinner label="Loading prompt…" />
          ) : (
            <>
              <pre className="mb-3 max-h-56 overflow-y-auto whitespace-pre-wrap rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 font-mono-num text-xs leading-relaxed text-text-muted">
                {promptData?.prompt}
              </pre>
              <CopyButton text={promptData?.prompt ?? ''} />
            </>
          )}
        </Card>

        <Card>
          <div className="mb-3 flex items-center gap-2">
            <ArrowUpTrayIcon className="h-5 w-5 text-primary" />
            <span className="font-medium">2. Paste what the AI gives back</span>
          </div>
          <textarea
            value={pasted}
            onChange={(e) => setPasted(e.target.value)}
            placeholder='{"items": [{"name": "Pizza", "price": 5000}]}'
            rows={8}
            className="mb-3 w-full rounded-xl border border-[var(--color-border)] bg-transparent p-3 font-mono-num text-sm outline-none"
          />
          <Button fullWidth loading={importMutation.isPending} disabled={!pasted.trim()} onClick={() => importMutation.mutate()}>
            Import items
          </Button>
        </Card>
      </PageTransition>
    </Shell>
  )
}
