import { AnimatePresence, motion } from 'framer-motion'
import { ExclamationTriangleIcon } from '@heroicons/react/24/solid'

export function ErrorBanner({ message }: { message: string | null }) {
  return (
    <AnimatePresence>
      {message && (
        <motion.div
          role="alert"
          aria-live="polite"
          initial={{ opacity: 0, y: -8, height: 0 }}
          animate={{ opacity: 1, y: 0, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.18 }}
          className="mb-3 flex items-start gap-2 overflow-hidden rounded-xl border border-accent/30 bg-accent/10 px-3.5 py-2.5 text-sm text-accent"
        >
          <ExclamationTriangleIcon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{message}</span>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
