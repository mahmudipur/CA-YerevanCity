import { create } from 'zustand'

type Theme = 'light' | 'dark' | 'system'

interface UiState {
  theme: Theme
  setTheme: (t: Theme) => void
  toggleTheme: () => void
  navDirection: 1 | -1
  setNavDirection: (d: 1 | -1) => void
}

function applyTheme(theme: Theme) {
  const root = document.documentElement
  if (theme === 'system') {
    root.removeAttribute('data-theme')
  } else {
    root.setAttribute('data-theme', theme)
  }
}

const stored = (localStorage.getItem('yc-split-theme') as Theme | null) ?? 'system'
applyTheme(stored)

export const useUiStore = create<UiState>((set, get) => ({
  theme: stored,
  setTheme: (t) => {
    localStorage.setItem('yc-split-theme', t)
    applyTheme(t)
    set({ theme: t })
  },
  toggleTheme: () => {
    const current = get().theme
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const effectiveDark = current === 'dark' || (current === 'system' && systemDark)
    get().setTheme(effectiveDark ? 'light' : 'dark')
  },
  navDirection: 1,
  setNavDirection: (d) => set({ navDirection: d }),
}))
