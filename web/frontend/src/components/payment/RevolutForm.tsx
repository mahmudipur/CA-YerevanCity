import { motion } from 'framer-motion'
import type { Currency } from '../../api/types'

interface Props {
  rate: string
  eurPaid: string
  isWeekend: boolean
  isFairUsage: boolean
  onChange: (patch: Partial<{ rate: string; eurPaid: string; isWeekend: boolean; isFairUsage: boolean }>) => void
  preview: Currency | null
  previewLoading: boolean
}

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="flex min-h-11 cursor-pointer items-center justify-between gap-3 rounded-xl border border-[var(--color-border)] bg-surface px-3.5 py-2.5">
      <span className="text-sm font-medium">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative h-7 w-12 shrink-0 cursor-pointer rounded-full transition-colors ${checked ? 'bg-primary' : 'bg-[var(--color-border)]'}`}
      >
        <motion.span
          className="absolute top-0.5 left-0.5 h-6 w-6 rounded-full bg-white shadow"
          animate={{ x: checked ? 20 : 0 }}
          transition={{ type: 'spring', stiffness: 500, damping: 32 }}
        />
      </button>
    </label>
  )
}

export function RevolutForm({ rate, eurPaid, isWeekend, isFairUsage, onChange, preview, previewLoading }: Props) {
  return (
    <div className="space-y-3">
      <label className="block">
        <span className="mb-1.5 block text-sm font-medium text-text-muted">EUR → AMD rate</span>
        <input
          type="number"
          inputMode="decimal"
          placeholder="e.g. 411.50"
          value={rate}
          onChange={(e) => onChange({ rate: e.target.value })}
          className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 font-mono-num outline-none"
        />
      </label>
      <label className="block">
        <span className="mb-1.5 block text-sm font-medium text-text-muted">Total EUR paid</span>
        <input
          type="number"
          inputMode="decimal"
          placeholder="e.g. 25.00"
          value={eurPaid}
          onChange={(e) => onChange({ eurPaid: e.target.value })}
          className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 font-mono-num outline-none"
        />
      </label>
      <Toggle checked={isWeekend} onChange={(v) => onChange({ isWeekend: v })} label="Weekend purchase (+1%)" />
      <Toggle checked={isFairUsage} onChange={(v) => onChange({ isFairUsage: v })} label="Exchange fair usage fee (+1%)" />

      {preview && preview.method === 'revolut' && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-primary/30 bg-primary/10 p-3.5"
        >
          <div className="mb-2 flex items-baseline justify-between text-sm">
            <span className="text-text-muted">Total paid</span>
            <span className="font-mono-num font-semibold">€{preview.eur_effective.toFixed(2)}</span>
          </div>
          <div className="space-y-1">
            {Object.entries(preview.eur_per_person).map(([name, amt]) => (
              <div key={name} className="flex items-baseline justify-between text-sm">
                <span>{name}</span>
                <span className="font-mono-num">€{amt.toFixed(2)}</span>
              </div>
            ))}
          </div>
          {previewLoading && <div className="mt-1 text-xs text-text-muted">Updating…</div>}
        </motion.div>
      )}
    </div>
  )
}
