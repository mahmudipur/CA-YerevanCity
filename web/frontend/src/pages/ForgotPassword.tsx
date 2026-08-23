import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { CopyButton } from '../components/common/CopyButton'
import { PageTransition } from '../components/common/PageTransition'
import { authApi } from '../api/endpoints'
import { ApiError } from '../api/client'
import { useAuthStore } from '../store/authStore'
import type { RecoveryCodeResponse } from '../api/types'

export function ForgotPassword() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const setUser = useAuthStore((s) => s.setUser)
  const [username, setUsername] = useState('')
  const [recoveryCode, setRecoveryCode] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RecoveryCodeResponse | null>(null)
  const [acknowledged, setAcknowledged] = useState(false)

  const reset = useMutation({
    mutationFn: () => authApi.forgotPassword({ username: username.trim(), recovery_code: recoveryCode, new_password: newPassword }),
    onSuccess: (res) => {
      // Synchronous cache write, not invalidate-and-refetch — see Menu.tsx's
      // sign-out handler for why an async refetch would race navigate().
      setError(null)
      setResult(res)
      setUser(res)
      qc.setQueryData(['auth-me'], res)
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Invalid username or recovery code.'),
  })

  const continueToApp = () => {
    navigate(result?.yc_linked ? '/' : '/link-yc', { replace: true })
  }

  if (result) {
    return (
      <Shell title="New recovery code" subtitle="Your old one no longer works">
        <PageTransition>
          <Card>
            <ExclamationTriangleIcon className="mx-auto mb-2 h-8 w-8 text-amber-500" />
            <p className="mb-3 text-center text-sm text-text-muted">
              Your password was reset. That recovery code was single-use — here's a new one to save.
            </p>
            <div className="mb-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3.5 py-3 text-center">
              <code className="font-mono-num text-lg tracking-wider">{result.recovery_code}</code>
            </div>
            <div className="mb-3">
              <CopyButton text={result.recovery_code} label="Copy recovery code" />
            </div>
            <label className="mb-3 flex cursor-pointer items-start gap-2 text-sm text-text-muted">
              <input
                type="checkbox"
                checked={acknowledged}
                onChange={(e) => setAcknowledged(e.target.checked)}
                className="mt-0.5"
              />
              I've saved this recovery code somewhere safe.
            </label>
            <Button fullWidth disabled={!acknowledged} onClick={continueToApp}>
              Continue
            </Button>
          </Card>
        </PageTransition>
      </Shell>
    )
  }

  return (
    <Shell title="Forgot password" subtitle="Reset with your recovery code">
      <PageTransition>
        <Card>
          <ErrorBanner message={error} />
          <form
            onSubmit={(e) => {
              e.preventDefault()
              reset.mutate()
            }}
            className="space-y-3"
          >
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-text-muted">Username</span>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus
                className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-text-muted">Recovery code</span>
              <input
                value={recoveryCode}
                onChange={(e) => setRecoveryCode(e.target.value.toUpperCase())}
                placeholder="XXXX-XXXX-XXXX"
                className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 text-center font-mono-num tracking-wider outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-text-muted">New password</span>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
                className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 outline-none"
              />
              <span className="mt-1.5 block text-xs text-text-muted">At least 8 characters.</span>
            </label>
            <Button
              type="submit"
              fullWidth
              loading={reset.isPending}
              disabled={!username || !recoveryCode || newPassword.length < 8}
            >
              Reset password
            </Button>
            <Link to="/login" className="block text-center text-sm text-text-muted hover:text-text">
              Back to sign in
            </Link>
          </form>
        </Card>
        <p className="mt-3 text-xs text-text-muted">
          Lost your recovery code too? Ask whoever runs this app to reset your password for you.
        </p>
      </PageTransition>
    </Shell>
  )
}
