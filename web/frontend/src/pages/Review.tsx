import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { CheckIcon } from '@heroicons/react/24/solid'
import { Shell } from '../components/common/Shell'
import { Button } from '../components/common/Button'
import { Spinner } from '../components/common/Spinner'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { PageTransition } from '../components/common/PageTransition'
import { ReviewList } from '../components/wizard/ReviewList'
import { sessionsApi } from '../api/endpoints'
import { ApiError } from '../api/client'
import { useState } from 'react'

export function Review() {
  const { sessionId = '' } = useParams()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['review', sessionId],
    queryFn: () => sessionsApi.review(sessionId),
  })

  const finish = useMutation({
    mutationFn: () => sessionsApi.finish(sessionId),
    onSuccess: () => navigate(`/sessions/${sessionId}/summary`),
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not finish the split.'),
  })

  if (isLoading || !data) {
    return (
      <Shell title="Review" onBack={() => navigate(-1)}>
        <Spinner />
      </Shell>
    )
  }

  return (
    <Shell title="Review" subtitle="Pick an item to edit, or finish" onBack={() => navigate(-1)}>
      <PageTransition>
        <ErrorBanner message={error} />
        <ReviewList
          rows={data.items}
          onEdit={(index) => navigate(`/sessions/${sessionId}/items/${index}?from=review`)}
        />
        <Button
          fullWidth
          className="mt-4"
          icon={<CheckIcon className="h-4 w-4" />}
          disabled={!data.all_assigned}
          loading={finish.isPending}
          onClick={() => finish.mutate()}
        >
          Finish
        </Button>
        {!data.all_assigned && (
          <p className="mt-2 text-center text-xs text-text-muted">Assign every item before finishing.</p>
        )}
      </PageTransition>
    </Shell>
  )
}
