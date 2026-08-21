import { motion } from 'framer-motion'
import type { AssignResult } from '../../api/types'

export function ItemResultCallout({ result }: { result: AssignResult }) {
  const entries = Object.entries(result.assignments).filter(([, v]) => v > 0)
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 24 }}
      className="mt-3 rounded-xl border border-primary/30 bg-primary/10 px-3.5 py-3"
    >
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
        {entries.map(([name, amount]) => (
          <span key={name} className="font-medium">
            {name}: <span className="font-mono-num">{amount.toLocaleString()} AMD</span>
          </span>
        ))}
      </div>
    </motion.div>
  )
}
