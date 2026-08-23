import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { ArrowRightOnRectangleIcon, Cog6ToothIcon, ShoppingBagIcon, PencilSquareIcon, ClockIcon } from '@heroicons/react/24/outline'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { PageTransition } from '../components/common/PageTransition'
import { authApi } from '../api/endpoints'
import { useAuthStore } from '../store/authStore'

export function Menu() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const setAnonymous = useAuthStore((s) => s.setAnonymous)
  const user = useAuthStore((s) => s.user)

  const signOut = useMutation({
    mutationFn: () => authApi.telegramLogout(),
    onSuccess: () => {
      // Synchronous cache write, not invalidate-and-refetch: a real network
      // round-trip here would race AuthGate's own redirect (it re-renders
      // the instant setAnonymous() fires, before navigate() below even
      // runs), which is what caused sign-out to bounce back into the app
      // and need a second click.
      qc.setQueryData(['auth-me'], null)
      setAnonymous()
      navigate('/login', { replace: true })
    },
  })

  const options = [
    {
      icon: ShoppingBagIcon,
      title: 'Yerevan City order',
      subtitle: 'Split a delivery order by item',
      onClick: () => navigate('/orders'),
    },
    {
      icon: PencilSquareIcon,
      title: 'Manual expense',
      subtitle: 'Restaurant, cafe, or any other bill',
      onClick: () => navigate('/manual/choice'),
    },
  ]

  return (
    <Shell
      title="Split"
      subtitle={user?.first_name ? `Hi, ${user.first_name}` : 'What would you like to split?'}
      right={
        <button
          type="button"
          onClick={() => signOut.mutate()}
          disabled={signOut.isPending}
          aria-label="Sign out"
          className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-text-muted transition-colors hover:bg-[var(--color-surface-muted)] disabled:opacity-50"
        >
          <ArrowRightOnRectangleIcon className="h-5 w-5" />
        </button>
      }
    >
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

          <button
            type="button"
            onClick={() => navigate('/history')}
            className="flex w-full min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl py-3 text-sm font-medium text-text-muted hover:text-text"
          >
            <ClockIcon className="h-4 w-4" />
            View past splits
          </button>

          <button
            type="button"
            onClick={() => navigate('/account')}
            className="flex w-full min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl py-3 text-sm font-medium text-text-muted hover:text-text"
          >
            <Cog6ToothIcon className="h-4 w-4" />
            Account settings
          </button>
        </div>
      </PageTransition>
    </Shell>
  )
}
