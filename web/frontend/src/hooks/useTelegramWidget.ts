import { useEffect, useRef } from 'react'
import type { TelegramLoginPayload } from '../api/types'

declare global {
  interface Window {
    onTelegramAuth?: (user: TelegramLoginPayload) => void
  }
}

const WIDGET_SCRIPT_SRC = 'https://telegram.org/js/telegram-widget.js?22'

/** Injects the Telegram Login Widget into the returned ref's container.
 * Used both for a fresh sign-in (Login.tsx) and for linking Telegram onto
 * an already-authenticated account (Account.tsx) — same widget, different
 * callback. No-ops (renders nothing) when botUsername is empty. */
export function useTelegramWidget(botUsername: string | undefined, onAuth: (user: TelegramLoginPayload) => void) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!botUsername || !containerRef.current) return

    window.onTelegramAuth = (user) => onAuth(user)

    const script = document.createElement('script')
    script.src = WIDGET_SCRIPT_SRC
    script.async = true
    script.setAttribute('data-telegram-login', botUsername)
    script.setAttribute('data-size', 'large')
    script.setAttribute('data-radius', '12')
    script.setAttribute('data-onauth', 'onTelegramAuth(user)')
    script.setAttribute('data-request-access', 'write')
    containerRef.current.appendChild(script)

    return () => {
      containerRef.current?.replaceChildren()
      delete window.onTelegramAuth
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [botUsername])

  return containerRef
}
