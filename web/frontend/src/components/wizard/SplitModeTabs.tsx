import { motion } from 'framer-motion'
import clsx from 'clsx'
import type { SplitMode } from '../../api/types'

const MODES: { label: string; value: SplitMode }[] = [
  { label: 'Equal', value: 'equal' },
  { label: '%', value: 'percentage' },
  { label: 'AMD', value: 'amount' },
  { label: 'Ratio', value: 'part' },
]

export function SplitModeTabs({ value, onChange }: { value: SplitMode; onChange: (m: SplitMode) => void }) {
  return (
    <div className="mb-3">
      <div className="mb-2 text-sm font-medium text-text-muted">How to split?</div>
      <div className="flex gap-1 rounded-xl bg-[var(--color-surface-muted)] p-1">
        {MODES.map((m) => (
          <button
            key={m.value}
            type="button"
            onClick={() => onChange(m.value)}
            className={clsx(
              'relative min-h-9 flex-1 cursor-pointer rounded-lg px-2 py-1.5 text-sm font-semibold transition-colors',
              value === m.value ? 'text-on-primary' : 'text-text-muted hover:text-text',
            )}
          >
            {value === m.value && (
              <motion.span
                layoutId="split-mode-active"
                className="absolute inset-0 rounded-lg bg-primary"
                transition={{ type: 'spring', stiffness: 400, damping: 32 }}
              />
            )}
            <span className="relative">{m.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
