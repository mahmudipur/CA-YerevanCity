import { create } from 'zustand'
import type { TelegramUser } from '../api/types'

type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

interface AuthState {
  user: TelegramUser | null
  status: AuthStatus
  setUser: (u: TelegramUser) => void
  setAnonymous: () => void
}

// No localStorage persistence of the user object — the httpOnly session
// cookie is the actual source of truth; this is just a client-side cache
// hydrated from GET /api/auth/me on app load (see App.tsx's AuthGate).
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  status: 'loading',
  setUser: (u) => set({ user: u, status: 'authenticated' }),
  setAnonymous: () => set({ user: null, status: 'anonymous' }),
}))
