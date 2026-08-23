import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Spinner } from '../components/common/Spinner'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { PageTransition } from '../components/common/PageTransition'
import { authApi } from '../api/endpoints'
import { ApiError } from '../api/client'
import { useAuthStore } from '../store/authStore'
import { useTelegramWidget } from '../hooks/useTelegramWidget'
import type { TelegramLoginPayload, UserProfile } from '../api/types'

export function Login() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const setUser = useAuthStore((s) => s.setUser)
  const [error, setError] = useState<string | null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  // bot_username empty/missing -> Telegram login isn't configured; the
  // widget section is skipped entirely (no error, no broken button) and
  // username/password is the only option shown.
  const { data: config } = useQuery({
    queryKey: ['telegram-config'],
    queryFn: authApi.telegramConfig,
  })
  const telegramConfigured = Boolean(config?.bot_username)

  const afterLogin = (user: UserProfile) => {
    // Synchronous cache write, not invalidate-and-refetch — see Menu.tsx's
    // sign-out handler for why an async refetch here would race navigate().
    setError(null)
    setUser(user)
    qc.setQueryData(['auth-me'], user)
    navigate(user.yc_linked ? '/' : '/link-yc', { replace: true })
  }

  const telegramCallback = useMutation({
    mutationFn: (payload: TelegramLoginPayload) => authApi.telegramCallback(payload),
    onSuccess: afterLogin,
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Telegram sign-in failed.'),
  })

  const passwordLogin = useMutation({
    mutationFn: () => authApi.login(username.trim(), password),
    onSuccess: afterLogin,
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Sign-in failed.'),
  })

  const widgetRef = useTelegramWidget(config?.bot_username, (user) => telegramCallback.mutate(user))

  return (
    <Shell title="Sign in" subtitle="Yerevan City Split">
      <PageTransition>
        <ErrorBanner message={error} />

        {telegramConfigured && (
          <Card className="mb-4 text-center">
            {telegramCallback.isPending ? <Spinner /> : <div ref={widgetRef} className="flex justify-center" />}
          </Card>
        )}

        {telegramConfigured && (
          <div className="my-4 flex items-center gap-3 text-xs text-text-muted">
            <div className="h-px flex-1 bg-[var(--color-border)]" />
            or
            <div className="h-px flex-1 bg-[var(--color-border)]" />
          </div>
        )}

        <Card>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              passwordLogin.mutate()
            }}
            className="space-y-3"
          >
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-text-muted">Username</span>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus={!telegramConfigured}
                className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-text-muted">Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 outline-none"
              />
            </label>
            <Button type="submit" fullWidth loading={passwordLogin.isPending} disabled={!username || !password}>
              Sign in
            </Button>
            <div className="flex items-center justify-between text-xs">
              <Link to="/signup" className="text-accent hover:underline">
                Create an account
              </Link>
              <Link to="/forgot-password" className="text-text-muted hover:underline">
                Forgot password?
              </Link>
            </div>
          </form>
        </Card>
      </PageTransition>
    </Shell>
  )
}
