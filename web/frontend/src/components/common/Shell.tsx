import { ChevronLeftIcon } from '@heroicons/react/24/outline'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { ThemeToggle } from './ThemeToggle'

interface ShellProps {
  title: string
  subtitle?: string
  onBack?: () => void
  right?: ReactNode
  children: ReactNode
}

export function Shell({ title, subtitle, onBack, right, children }: ShellProps) {
  const navigate = useNavigate()
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-lg flex-col px-4 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-[max(0.75rem,env(safe-area-inset-top))] sm:max-w-xl">
      <header className="mb-4 flex items-center gap-2">
        {onBack ? (
          <button
            type="button"
            onClick={() => (onBack ? onBack() : navigate(-1))}
            aria-label="Go back"
            className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-text-muted transition-colors hover:bg-[var(--color-surface-muted)]"
          >
            <ChevronLeftIcon className="h-5 w-5" />
          </button>
        ) : (
          <div className="w-11 shrink-0" />
        )}
        <div className="min-w-0 flex-1 text-center">
          <h1 className="truncate font-display text-lg leading-tight">{title}</h1>
          {subtitle && <p className="truncate text-xs text-text-muted">{subtitle}</p>}
        </div>
        <div className="flex w-11 shrink-0 justify-end">{right ?? <ThemeToggle />}</div>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  )
}
