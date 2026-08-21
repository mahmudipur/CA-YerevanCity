import { motion } from 'framer-motion'

export function ProgressBar({ index, total }: { index: number; total: number }) {
  const pct = total > 0 ? ((index + 1) / total) * 100 : 0
  return (
    <div className="mb-5">
      <div className="mb-1.5 flex items-center justify-between text-xs font-medium text-text-muted">
        <span>
          Item {index + 1} of {total}
        </span>
        <span>{Math.round(pct)}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--color-surface-muted)]">
        <motion.div
          className="h-full rounded-full bg-primary"
          initial={false}
          animate={{ width: `${pct}%` }}
          transition={{ type: 'spring', stiffness: 300, damping: 32 }}
        />
      </div>
    </div>
  )
}
