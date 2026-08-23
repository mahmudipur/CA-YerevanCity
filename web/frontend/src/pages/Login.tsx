import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Shell } from '../components/common/Shell'
import { Card } from '../components/common/Card'
import { Spinner } from '../components/common/Spinner'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { PageTransition } from '../components/common/PageTransition'
import { authApi } from '../api/endpoints'
import { ApiError } from '../api/client'
import { useAuthStore } from '../store/authStore'
import type { TelegramLoginPayload } from '../api/types'

declare global {
  interface Window {
    onTelegramAuth?: (user: TelegramLoginPayload) => void
  }
}

const WIDGET_SCRIPT_SRC = 'https://telegram.org/js/telegram-widget.js?22'

export function Login() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const setUser = useAuthStore((s) => s.setUser)
  const [error, setError] = useState<string | null>(null)
  const widgetContainer = useRef<HTMLDivElement | null>(null)

  const { data: config, isLoading: configLoading } = useQuery({
    queryKey: ['telegram-config'],
    queryFn: authApi.telegramConfig,
  })

  const callback = useMutation({
    mutationFn: (payload: TelegramLoginPayload) => authApi.telegramCallback(payload),
    onSuccess: async (user) => {
      setError(null)
      setUser(user)
      await qc.invalidateQueries({ queryKey: ['auth-me'] })
      navigate(user.yc_linked ? '/' : '/link-yc', { replace: true })
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Telegram sign-in failed.'),
  })

  useEffect(() => {
    if (!config?.bot_username || !widgetContainer.current) return

    window.onTelegramAuth = (user) => callback.mutate(user)

    const script = document.createElement('script')
    script.src = WIDGET_SCRIPT_SRC
    script.async = true
    script.setAttribute('data-telegram-login', config.bot_username)
    script.setAttribute('data-size', 'large')
    script.setAttribute('data-radius', '12')
    script.setAttribute('data-onauth', 'onTelegramAuth(user)')
    script.setAttribute('data-request-access', 'write')
    widgetContainer.current.appendChild(script)

    return () => {
      widgetContainer.current?.replaceChildren()
      delete window.onTelegramAuth
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config?.bot_username])

  return (
    <Shell title="Sign in" subtitle="Yerevan City Split">
      <PageTransition>
        <Card className="text-center">
          <ErrorBanner message={error} />
          <p className="mb-4 text-sm text-text-muted">
            Sign in with Telegram to get your own account — everyone's splits, orders, and Yerevan City login stay
            separate.
          </p>
          {configLoading ? (
            <Spinner />
          ) : !config?.bot_username ? (
            <ErrorBanner message="Telegram login isn't configured on this server yet." />
          ) : callback.isPending ? (
            <Spinner />
          ) : (
            <div ref={widgetContainer} className="flex justify-center" />
          )}
        </Card>
      </PageTransition>
    </Shell>
  )
}
