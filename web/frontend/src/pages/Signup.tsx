import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'
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

export function Signup() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const setUser = useAuthStore((s) => s.setUser)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RecoveryCodeResponse | null>(null)
  const [acknowledged, setAcknowledged] = useState(false)

  const signup = useMutation({
    mutationFn: () => authApi.signup({ username: username.trim(), password }),
    onSuccess: (res) => {
      // Synchronous cache write, not invalidate-and-refetch — see Menu.tsx's
      // sign-out handler for why an async refetch would race navigate().
      setError(null)
      setResult(res)
      setUser(res)
      qc.setQueryData(['auth-me'], res)
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not create an account.'),
  })

  const continueToApp = () => {
    navigate(result?.yc_linked ? '/' : '/link-yc', { replace: true })
  }

  if (result) {
    return (
      <Shell title="Save your recovery code" subtitle="You will not see this again">
        <PageTransition>
          <Card>
            <ExclamationTriangleIcon className="mx-auto mb-2 h-8 w-8 text-amber-500" />
            <p className="mb-3 text-center text-sm text-text-muted">
              There's no email or SMS to recover your account with — this code is the only way back in if you forget
              your password. Save it somewhere safe now.
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
    <Shell title="Create an account" subtitle="Yerevan City Split">
      <PageTransition>
        <Card>
          <ErrorBanner message={error} />
          <form
            onSubmit={(e) => {
              e.preventDefault()
              signup.mutate()
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
              <span className="mt-1.5 block text-xs text-text-muted">3-32 characters: letters, numbers, . _ -</span>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-text-muted">Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 outline-none"
              />
              <span className="mt-1.5 block text-xs text-text-muted">At least 8 characters.</span>
            </label>
            <Button
              type="submit"
              fullWidth
              loading={signup.isPending}
              disabled={username.trim().length < 3 || password.length < 8}
            >
              Create account
            </Button>
            <Link to="/login" className="block text-center text-sm text-text-muted hover:text-text">
              Already have an account? Sign in
            </Link>
          </form>
        </Card>
        <p className="mt-3 flex items-start gap-1.5 text-xs text-text-muted">
          <CheckCircleIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Yerevan City's own login is a separate step after this one.
        </p>
      </PageTransition>
    </Shell>
  )
}
