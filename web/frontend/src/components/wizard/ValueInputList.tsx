import { motion } from 'framer-motion'
import type { SplitMode } from '../../api/types'

const UNIT: Record<SplitMode, string> = {
  equal: '',
  percentage: '%',
  amount: 'AMD',
  part: 'parts',
}

interface Props {
  mode: SplitMode
  selected: string[]
  values: Record<string, string>
  onChange: (name: string, raw: string) => void
}

export function ValueInputList({ mode, selected, values, onChange }: Props) {
  if (mode === 'equal' || selected.length === 0) return null
  const unit = UNIT[mode]

  return (
    <motion.div
      className="mb-3 space-y-2"
      initial="hidden"
      animate="show"
      variants={{ show: { transition: { staggerChildren: 0.04 } } }}
    >
      {selected.map((name) => (
        <motion.label
          key={name}
          variants={{ hidden: { opacity: 0, y: 6 }, show: { opacity: 1, y: 0 } }}
          className="flex items-center justify-between gap-3 rounded-xl border border-[var(--color-border)] bg-surface px-3.5 py-2"
        >
          <span className="text-sm font-medium">{name}</span>
          <span className="flex items-center gap-1.5">
            <input
              type="number"
              inputMode="decimal"
              value={values[name] ?? ''}
              onChange={(e) => onChange(name, e.target.value)}
              className="w-24 min-h-11 rounded-lg border border-[var(--color-border)] bg-transparent px-2.5 py-1.5 text-right font-mono-num text-sm outline-none"
              aria-label={`${name} ${unit}`}
            />
            <span className="w-11 text-xs text-text-muted">{unit}</span>
          </span>
        </motion.label>
      ))}
    </motion.div>
  )
}
