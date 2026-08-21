import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { Shell } from '../components/common/Shell'
import { Button } from '../components/common/Button'
import { Spinner } from '../components/common/Spinner'
import { PageTransition } from '../components/common/PageTransition'
import { TotalsTable } from '../components/summary/TotalsTable'
import { sessionsApi } from '../api/endpoints'

export function Summary() {
  const { sessionId = '' } = useParams()
  const navigate = useNavigate()

  const { data: session } = useQuery({ queryKey: ['session', sessionId], queryFn: () => sessionsApi.get(sessionId) })
  const { data: finish, isLoading } = useQuery({
    queryKey: ['finish', sessionId],
    queryFn: () => sessionsApi.finish(sessionId),
  })

  if (isLoading || !finish || !session) {
    return (
      <Shell title="Summary" onBack={() => navigate(-1)}>
        <Spinner />
      </Shell>
    )
  }

  return (
    <Shell title="Summary" subtitle="Per-person totals" onBack={() => navigate(-1)}>
      <PageTransition>
        <TotalsTable
          participants={session.participants}
          totals={finish.totals}
          grandTotal={finish.grand_total}
          orderTotal={finish.order_total}
          discrepancyWarning={finish.discrepancy_warning}
        />
        <Button fullWidth className="mt-5" onClick={() => navigate(`/sessions/${sessionId}/payment`)}>
          Continue to payment
        </Button>
      </PageTransition>
    </Shell>
  )
}
