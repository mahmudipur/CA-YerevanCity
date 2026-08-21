import { motion } from 'framer-motion'
import { ExclamationTriangleIcon } from '@heroicons/react/24/solid'
import type { PersonTotal } from '../../api/types'

interface Props {
  participants: string[]
  totals: Record<string, PersonTotal>
  grandTotal: number
  orderTotal: number
  discrepancyWarning: boolean
}

export function TotalsTable({ participants, totals, grandTotal, orderTotal, discrepancyWarning }: Props) {
  const maxTotal = Math.max(1, ...participants.map((p) => totals[p]?.total ?? 0))

  return (
    <div className="space-y-3">
      {participants.map((p, i) => {
        const t = totals[p] ?? { items: 0, fees: 0, total: 0 }
        const itemsPct = (t.items / maxTotal) * 100
        const feesPct = (t.fees / maxTotal) * 100
        return (
          <div key={p} className="rounded-xl border border-[var(--color-border)] bg-surface p-3.5">
            <div className="mb-2 flex items-baseline justify-between">
              <span className="font-medium">{p}</span>
              <span className="font-mono-num text-lg font-semibold">{t.total.toLocaleString()} AMD</span>
            </div>
            <div className="flex h-2.5 overflow-hidden rounded-full bg-[var(--color-surface-muted)]">
              <motion.div
                className="h-full bg-primary"
                initial={{ width: 0 }}
                animate={{ width: `${itemsPct}%` }}
                transition={{ delay: i * 0.05, type: 'spring', stiffness: 260, damping: 26 }}
              />
              <motion.div
                className="h-full bg-accent/60"
                initial={{ width: 0 }}
                animate={{ width: `${feesPct}%` }}
                transition={{ delay: i * 0.05 + 0.03, type: 'spring', stiffness: 260, damping: 26 }}
              />
            </div>
            <div className="mt-1.5 flex justify-between text-xs text-text-muted">
              <span>Items: {t.items.toLocaleString()} AMD</span>
              {t.fees > 0 && <span>Fees: {t.fees.toLocaleString()} AMD</span>}
            </div>
          </div>
        )
      })}

      <div className="flex items-baseline justify-between border-t border-[var(--color-border)] pt-3">
        <span className="font-display text-base">Grand total</span>
        <span className="font-mono-num text-xl font-bold">{grandTotal.toLocaleString()} AMD</span>
      </div>
      <div className="text-right text-xs text-text-muted">Order total: {orderTotal.toLocaleString()} AMD</div>

      {discrepancyWarning && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-xl border border-accent/30 bg-accent/10 px-3.5 py-2.5 text-sm text-accent"
        >
          <ExclamationTriangleIcon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>Discrepancy of {Math.abs(grandTotal - orderTotal).toLocaleString()} AMD. Check for unassigned items or rounding.</span>
        </div>
      )}
    </div>
  )
}
