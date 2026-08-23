import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ExclamationTriangleIcon, KeyIcon, LinkIcon } from '@heroicons/react/24/outline'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { CopyButton } from '../components/common/CopyButton'
import { PageTransition } from '../components/common/PageTransition'
import { authApi } from '../api/endpoints'
import { ApiError } from '../api/client'
import { useAuthStore } from '../store/authStore'
import { useTelegramWidget } from '../hooks/useTelegramWidget'
import type { TelegramLoginPayload } from '../api/types'

export function Account() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const [error, setError] = useState<string | null>(null)
  const [newRecoveryCode, setNewRecoveryCode] = useState<string | null>(null)
  const [setPasswordUsername, setSetPasswordUsername] = useState('')
  const [setPasswordValue, setSetPasswordValue] = useState('')
  const [newRecoveryCodeFromSetPassword, setNewRecoveryCodeFromSetPassword] = useState<string | null>(null)

  const { data: config } = useQuery({ queryKey: ['telegram-config'], queryFn: authApi.telegramConfig })
  const telegramConfigured = Boolean(config?.bot_username)

  const linkTelegram = useMutation({
    mutationFn: (payload: TelegramLoginPayload) => authApi.telegramLink(payload),
    onSuccess: (updated) => {
      setError(null)
      setUser(updated)
      qc.setQueryData(['auth-me'], updated)
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not link Telegram.'),
  })

  const regenerate = useMutation({
    mutationFn: () => authApi.regenerateRecoveryCode(),
    onSuccess: (res) => {
      setError(null)
      setNewRecoveryCode(res.recovery_code)
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not regenerate recovery code.'),
  })

  const setPassword = useMutation({
    mutationFn: () => authApi.setPassword(setPasswordUsername.trim(), setPasswordValue),
    onSuccess: (res) => {
      setError(null)
      setNewRecoveryCodeFromSetPassword(res.recovery_code)
      // The endpoint only returns the recovery code, not a full profile —
      // patch the known-changed fields locally rather than round-tripping.
      if (user) {
        const updated = { ...user, username: setPasswordUsername.trim(), has_password: true }
        setUser(updated)
        qc.setQueryData(['auth-me'], updated)
      }
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not set a password.'),
  })

  const widgetRef = useTelegramWidget(config?.bot_username, (payload) => linkTelegram.mutate(payload))

  if (!user) return null

  return (
    <Shell title="Account" onBack={() => navigate(-1)}>
      <PageTransition>
        <ErrorBanner message={error} />

        <Card className="mb-4">
          <p className="font-display text-base">{user.first_name}</p>
          {user.username && <p className="text-sm text-text-muted">@{user.username}</p>}
          {user.telegram_username && <p className="text-sm text-text-muted">Telegram: @{user.telegram_username}</p>}
        </Card>

        {user.has_password && (
          <Card className="mb-4">
            <div className="mb-2 flex items-center gap-2">
              <KeyIcon className="h-5 w-5 text-text-muted" />
              <span className="font-medium">Recovery code</span>
            </div>
            {newRecoveryCode ? (
              <>
                <div className="mb-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3.5 py-3 text-center">
                  <code className="font-mono-num text-lg tracking-wider">{newRecoveryCode}</code>
                </div>
                <CopyButton text={newRecoveryCode} label="Copy recovery code" />
                <p className="mt-2 flex items-start gap-1.5 text-xs text-amber-600 dark:text-amber-400">
                  <ExclamationTriangleIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  Your old code no longer works — save this new one.
                </p>
              </>
            ) : (
              <>
                <p className="mb-3 text-sm text-text-muted">
                  Lost your recovery code, but still signed in? Generate a new one now (this invalidates the old one).
                </p>
                <Button fullWidth variant="secondary" loading={regenerate.isPending} onClick={() => regenerate.mutate()}>
                  Generate new recovery code
                </Button>
              </>
            )}
          </Card>
        )}

        {telegramConfigured && !user.telegram_linked && (
          <Card className="mb-4">
            <div className="mb-2 flex items-center gap-2">
              <LinkIcon className="h-5 w-5 text-text-muted" />
              <span className="font-medium">Connect Telegram</span>
            </div>
            <p className="mb-3 text-sm text-text-muted">Sign in with the same account from either method afterward.</p>
            <div ref={widgetRef} className="flex justify-center" />
          </Card>
        )}

        {!user.has_password && (
          <Card>
            <div className="mb-2 flex items-center gap-2">
              <KeyIcon className="h-5 w-5 text-text-muted" />
              <span className="font-medium">Set a password</span>
            </div>
            {newRecoveryCodeFromSetPassword ? (
              <>
                <p className="mb-3 text-sm text-text-muted">Password set. Save this recovery code:</p>
                <div className="mb-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3.5 py-3 text-center">
                  <code className="font-mono-num text-lg tracking-wider">{newRecoveryCodeFromSetPassword}</code>
                </div>
                <CopyButton text={newRecoveryCodeFromSetPassword} label="Copy recovery code" />
              </>
            ) : (
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  setPassword.mutate()
                }}
                className="space-y-3"
              >
                <p className="text-sm text-text-muted">
                  So you can also sign in without Telegram (useful if this server's config ever changes).
                </p>
                <input
                  value={setPasswordUsername}
                  onChange={(e) => setSetPasswordUsername(e.target.value)}
                  placeholder="Username"
                  autoComplete="username"
                  className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 outline-none"
                />
                <input
                  type="password"
                  value={setPasswordValue}
                  onChange={(e) => setSetPasswordValue(e.target.value)}
                  placeholder="Password"
                  autoComplete="new-password"
                  className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 outline-none"
                />
                <Button
                  type="submit"
                  fullWidth
                  loading={setPassword.isPending}
                  disabled={setPasswordUsername.trim().length < 3 || setPasswordValue.length < 8}
                >
                  Set password
                </Button>
              </form>
            )}
          </Card>
        )}
      </PageTransition>
    </Shell>
  )
}
