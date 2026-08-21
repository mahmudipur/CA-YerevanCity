import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { CheckCircleIcon, ArrowDownTrayIcon } from '@heroicons/react/24/solid'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Spinner } from '../components/common/Spinner'
import { PageTransition } from '../components/common/PageTransition'
import { sessionsApi, csvDownloadUrl } from '../api/endpoints'

export function Done() {
  const { sessionId = '' } = useParams()
  const navigate = useNavigate()

  const { data, isLoading, error } = useQuery({
    queryKey: ['save', sessionId],
    queryFn: () => sessionsApi.save(sessionId),
    retry: false,
  })

  if (isLoading) {
    return (
      <Shell title="Saving…">
        <Spinner label="Writing split file…" />
      </Shell>
    )
  }

  if (error || !data) {
    return (
      <Shell title="Done">
        <Card className="text-center text-sm text-accent">Could not save the split. Please go back and try again.</Card>
      </Shell>
    )
  }

  return (
    <Shell title="Done" right={<span />}>
      <PageTransition>
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: 'spring', stiffness: 260, damping: 22 }}
          className="flex flex-col items-center py-6 text-center"
        >
          <CheckCircleIcon className="mb-3 h-16 w-16 text-primary" />
          <h2 className="font-display text-xl">Split saved</h2>
          <p className="mt-1 text-sm text-text-muted">{data.split_id}</p>
        </motion.div>

        <div className="space-y-3">
          <Button fullWidth variant="secondary" icon={<ArrowDownTrayIcon className="h-4 w-4" />} onClick={() => window.open(csvDownloadUrl(data.split_id), '_blank')}>
            Download CSV
          </Button>
          <Button fullWidth onClick={() => navigate('/')}>
            Start another split
          </Button>
        </div>
      </PageTransition>
    </Shell>
  )
}
