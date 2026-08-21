import { MoonIcon, SunIcon } from '@heroicons/react/24/outline'
import { useUiStore } from '../../store/uiStore'

export function ThemeToggle() {
  const theme = useUiStore((s) => s.theme)
  const toggleTheme = useUiStore((s) => s.toggleTheme)
  const systemDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
  const isDark = theme === 'dark' || (theme === 'system' && systemDark)

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-text-muted transition-colors hover:bg-[var(--color-surface-muted)]"
    >
      {isDark ? <SunIcon className="h-5 w-5" /> : <MoonIcon className="h-5 w-5" />}
    </button>
  )
}
