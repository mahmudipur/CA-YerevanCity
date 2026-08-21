import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { PencilSquareIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { PageTransition } from '../components/common/PageTransition'

/** Shown immediately after picking "Manual expense" — before a session even
 * exists — so the AI-receipt option is the first thing people see, not
 * buried a few steps into the flow. */
export function ManualChoice() {
  const navigate = useNavigate()

  const options = [
    {
      icon: PencilSquareIcon,
      title: 'Enter items manually',
      subtitle: 'Type in name, price, and service for each item',
      onClick: () => navigate('/manual/new?via=manual'),
    },
    {
      icon: SparklesIcon,
      title: 'Scan a receipt with AI',
      subtitle: 'Send a photo to any AI, paste back the result',
      onClick: () => navigate('/manual/new?via=ai'),
    },
  ]

  return (
    <Shell title="Manual expense" subtitle="How would you like to add items?" onBack={() => navigate(-1)}>
      <PageTransition>
        <div className="space-y-3">
          {options.map((opt, i) => (
            <motion.button
              key={opt.title}
              type="button"
              onClick={opt.onClick}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              whileTap={{ scale: 0.98 }}
              className="w-full cursor-pointer text-left"
            >
              <Card className="flex items-center gap-4 transition-colors hover:bg-[var(--color-surface-muted)]">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <opt.icon className="h-6 w-6" />
                </div>
                <div className="min-w-0">
                  <div className="font-display text-base">{opt.title}</div>
                  <div className="text-sm text-text-muted">{opt.subtitle}</div>
                </div>
              </Card>
            </motion.button>
          ))}
        </div>
      </PageTransition>
    </Shell>
  )
}
