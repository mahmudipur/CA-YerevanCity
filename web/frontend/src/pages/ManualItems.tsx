import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { PlusIcon, SparklesIcon, TrashIcon } from '@heroicons/react/24/outline'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Spinner } from '../components/common/Spinner'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { PageTransition } from '../components/common/PageTransition'
import { UnitToggleInput } from '../components/common/UnitToggleInput'
import { sessionsApi } from '../api/endpoints'
import { ApiError } from '../api/client'

export function ManualItems() {
  const { sessionId = '' } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [name, setName] = useState('')
  const [price, setPrice] = useState('')
  const [serviceValue, setServiceValue] = useState('')
  const [serviceUnit, setServiceUnit] = useState<'%' | 'AMD'>('%')
  const [error, setError] = useState<string | null>(null)

  const { data: session, isLoading } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => sessionsApi.get(sessionId),
  })

  const addItem = useMutation({
    mutationFn: () =>
      sessionsApi.addManualItem(sessionId, {
        name: name.trim(),
        price: Number(price) || 0,
        service_raw: serviceValue.trim() ? `${serviceValue.trim()}${serviceUnit === '%' ? '%' : ''}` : '',
      }),
    onSuccess: (updated) => {
      setError(null)
      qc.setQueryData(['session', sessionId], updated)
      setName('')
      setPrice('')
      setServiceValue('')
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not add item.'),
  })

  const removeItem = useMutation({
    mutationFn: (index: number) => sessionsApi.removeManualItem(sessionId, index),
    onSuccess: (updated) => qc.setQueryData(['session', sessionId], updated),
  })

  if (isLoading || !session) {
    return (
      <Shell title="Items" onBack={() => navigate(-1)}>
        <Spinner />
      </Shell>
    )
  }

  const items = session.items

  return (
    <Shell title="Items" subtitle={session.session_name ?? undefined} onBack={() => navigate(-1)}>
      <PageTransition>
        <button
          type="button"
          onClick={() => navigate(`/sessions/${sessionId}/receipt-import`)}
          className="mb-4 flex min-h-11 w-full cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-primary/40 bg-primary/5 py-2.5 text-sm font-medium text-primary hover:bg-primary/10"
        >
          <SparklesIcon className="h-4 w-4" />
          Add more items by scanning a receipt with AI
        </button>

        <Card className="mb-4">
          <ErrorBanner message={error} />
          <form
            onSubmit={(e) => {
              e.preventDefault()
              if (!price) return
              addItem.mutate()
            }}
            className="space-y-3"
          >
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Item name"
              className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 outline-none"
            />
            <div className="flex gap-2">
              <input
                type="number"
                inputMode="decimal"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder="Price (AMD)"
                className="min-h-11 w-1/2 rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 font-mono-num outline-none"
              />
              <div className="w-1/2">
                <UnitToggleInput
                  value={serviceValue}
                  unit={serviceUnit}
                  onValueChange={setServiceValue}
                  onUnitChange={setServiceUnit}
                  placeholder="Service"
                />
              </div>
            </div>
            <Button type="submit" fullWidth icon={<PlusIcon className="h-4 w-4" />} loading={addItem.isPending}>
              Add item
            </Button>
          </form>
        </Card>

        <ul className="mb-4 space-y-2">
          <AnimatePresence initial={false}>
            {items.map((it, i) => (
              <motion.li
                key={`${it.name}-${i}`}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <div className="flex items-center justify-between rounded-xl border border-[var(--color-border)] bg-surface px-3.5 py-3">
                  <div>
                    <div className="font-medium">{it.name}</div>
                    <div className="text-xs text-text-muted">
                      Net: {it.net_price.toLocaleString()} AMD
                      {it.service ? ` (price ${it.price?.toLocaleString()} + service ${it.service.toLocaleString()})` : ''}
                    </div>
                  </div>
                  <button
                    type="button"
                    aria-label={`Remove ${it.name}`}
                    onClick={() => removeItem.mutate(i)}
                    className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-full text-text-muted hover:bg-[var(--color-surface-muted)] hover:text-accent"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>

        <Button fullWidth disabled={items.length === 0} onClick={() => navigate(`/sessions/${sessionId}/items/0`)}>
          Continue to split ({items.length} item{items.length === 1 ? '' : 's'})
        </Button>
      </PageTransition>
    </Shell>
  )
}
