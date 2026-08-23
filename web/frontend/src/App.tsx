import { useEffect } from 'react'
import { AnimatePresence } from 'framer-motion'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Login } from './pages/Login'
import { LinkYc } from './pages/LinkYc'
import { Menu } from './pages/Menu'
import { Orders } from './pages/Orders'
import { ManualChoice } from './pages/ManualChoice'
import { ManualNew } from './pages/ManualNew'
import { Roster } from './pages/Roster'
import { ReceiptImport } from './pages/ReceiptImport'
import { ManualItems } from './pages/ManualItems'
import { ItemAssign } from './pages/ItemAssign'
import { Review } from './pages/Review'
import { Summary } from './pages/Summary'
import { Payment } from './pages/Payment'
import { Done } from './pages/Done'
import { History } from './pages/History'
import { Spinner } from './components/common/Spinner'
import { authApi } from './api/endpoints'
import { useAuthStore } from './store/authStore'

/** First real route guard in this app. Three states: not logged into
 * Telegram at all -> only /login is reachable; logged in but haven't linked
 * a Yerevan City account yet -> only /link-yc is reachable; fully set up ->
 * everything else, and /login and /link-yc redirect away. */
function AuthGate({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const { status, user, setUser, setAnonymous } = useAuthStore()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['auth-me'],
    queryFn: authApi.me,
    retry: false,
  })

  useEffect(() => {
    if (isLoading) return
    if (data) setUser(data)
    else if (isError) setAnonymous()
  }, [data, isError, isLoading, setUser, setAnonymous])

  if (status === 'loading') {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Spinner />
      </div>
    )
  }

  const path = location.pathname

  if (status === 'anonymous') {
    return path === '/login' ? <>{children}</> : <Navigate to="/login" replace />
  }

  // authenticated
  if (path === '/login') return <Navigate to={user?.yc_linked ? '/' : '/link-yc'} replace />
  if (!user?.yc_linked && path !== '/link-yc') return <Navigate to="/link-yc" replace />
  return <>{children}</>
}

export default function App() {
  const location = useLocation()
  return (
    <AuthGate>
      <AnimatePresence mode="wait" initial={false}>
        <Routes location={location} key={location.pathname}>
          <Route path="/login" element={<Login />} />
          <Route path="/link-yc" element={<LinkYc />} />
          <Route path="/" element={<Menu />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/manual/choice" element={<ManualChoice />} />
          <Route path="/manual/new" element={<ManualNew />} />
          <Route path="/sessions/:sessionId/roster" element={<Roster />} />
          <Route path="/sessions/:sessionId/receipt-import" element={<ReceiptImport />} />
          <Route path="/sessions/:sessionId/manual-items" element={<ManualItems />} />
          <Route path="/sessions/:sessionId/items/:index" element={<ItemAssign />} />
          <Route path="/sessions/:sessionId/review" element={<Review />} />
          <Route path="/sessions/:sessionId/summary" element={<Summary />} />
          <Route path="/sessions/:sessionId/payment" element={<Payment />} />
          <Route path="/sessions/:sessionId/done" element={<Done />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </AnimatePresence>
    </AuthGate>
  )
}
