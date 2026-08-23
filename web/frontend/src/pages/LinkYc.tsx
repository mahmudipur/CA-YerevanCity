import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ArrowRightOnRectangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Spinner } from '../components/common/Spinner'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { PhoneInput } from '../components/common/PhoneInput'
import { authApi } from '../api/endpoints'
import { ApiError } from '../api/client'
import { PageTransition } from '../components/common/PageTransition'
import { COUNTRY_CODES, DEFAULT_COUNTRY } from '../data/countryCodes'
import { useAuthStore } from '../store/authStore'

function detectCountryCode(e164?: string | null): string {
  if (!e164) return DEFAULT_COUNTRY.code
  const match = COUNTRY_CODES.find((c) => e164.startsWith(c.code))
  return match?.code ?? DEFAULT_COUNTRY.code
}

/** Step 2, after Telegram login: link this account's own Yerevan City phone
 * number via the same OTP flow as before — now scoped to this Telegram
 * user, not a single shared account. */
export function LinkYc() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const { data: status, isLoading: statusLoading } = useQuery({ queryKey: ['auth-status'], queryFn: authApi.status })

  // Always start on the phone step — never assume a code was already sent
  // just because a phone number happens to be on file.
  const [phase, setPhase] = useState<'phone' | 'otp'>('phone')
  const [countryCode, setCountryCode] = useState(() => detectCountryCode(status?.phone_e164))
  const [national, setNational] = useState(status?.phone_local ?? '')
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sentTo, setSentTo] = useState('')

  const fullPhone = `${countryCode}${national}`

  const sendCode = useMutation({
    mutationFn: () => authApi.sendCode(national || undefined, fullPhone),
    onSuccess: (res) => {
      setError(null)
      setSentTo(res.phone_e164)
      setPhase('otp')
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Failed to send code.'),
  })

  const verify = useMutation({
    mutationFn: () => authApi.verify(code, sentTo),
    onSuccess: () => {
      setError(null)
      qc.invalidateQueries({ queryKey: ['auth-status'] })
      // Patch yc_linked locally rather than invalidate-and-refetch — see
      // Menu.tsx's sign-out handler for why an async refetch racing the
      // navigate() below would bounce the redirect back to /link-yc.
      if (user) {
        const updated = { ...user, yc_linked: true }
        setUser(updated)
        qc.setQueryData(['auth-me'], updated)
      }
      navigate('/', { replace: true })
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Verification failed.'),
  })

  const logout = useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: async () => {
      setError(null)
      await qc.invalidateQueries({ queryKey: ['auth-status'] })
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not sign out.'),
  })

  if (statusLoading) {
    return (
      <Shell title="Link Yerevan City" subtitle="One-time setup">
        <Spinner />
      </Shell>
    )
  }

  if (status?.authenticated) {
    return (
      <Shell title="Link Yerevan City" subtitle="One-time setup">
        <PageTransition>
          <ErrorBanner message={error} />
          <Card className="text-center">
            <CheckCircleIcon className="mx-auto mb-2 h-10 w-10 text-primary" />
            <p className="font-display text-lg">Yerevan City is linked</p>
            {status.phone_e164 && <p className="mb-4 text-sm text-text-muted">{status.phone_e164}</p>}
            <div className="space-y-2">
              <Button fullWidth onClick={() => navigate('/orders')}>
                Continue
              </Button>
              <Button
                fullWidth
                variant="secondary"
                icon={<ArrowRightOnRectangleIcon className="h-4 w-4" />}
                loading={logout.isPending}
                onClick={() => logout.mutate()}
              >
                Unlink Yerevan City
              </Button>
            </div>
          </Card>
        </PageTransition>
      </Shell>
    )
  }

  return (
    <Shell title="Link Yerevan City" subtitle="One-time setup">
      <PageTransition>
        <Card>
          <ErrorBanner message={error} />
          {phase === 'phone' ? (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                sendCode.mutate()
              }}
              className="space-y-3"
            >
              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-text-muted">Phone number</span>
                <PhoneInput
                  countryCode={countryCode}
                  national={national}
                  onCountryChange={setCountryCode}
                  onNationalChange={setNational}
                  disabled={sendCode.isPending}
                />
                <span className="mt-1.5 block text-xs text-text-muted">We'll text a code to {fullPhone || '…'}</span>
              </label>
              <Button type="submit" fullWidth loading={sendCode.isPending} disabled={national.length < 6}>
                Send code
              </Button>
            </form>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                verify.mutate()
              }}
              className="space-y-3"
            >
              <p className="text-sm text-text-muted">SMS sent to {sentTo}. Enter the 6-digit code.</p>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                autoFocus
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                placeholder="123456"
                className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 text-center font-mono-num text-lg tracking-[0.4em] outline-none"
              />
              <Button type="submit" fullWidth loading={verify.isPending} disabled={code.length !== 6}>
                Verify
              </Button>
              <button
                type="button"
                onClick={() => setPhase('phone')}
                className="w-full cursor-pointer text-center text-sm text-text-muted hover:text-text"
              >
                Change phone number
              </button>
            </form>
          )}
        </Card>
      </PageTransition>
    </Shell>
  )
}
