import { AnimatePresence } from 'framer-motion'
import { Route, Routes, useLocation } from 'react-router-dom'
import { Login } from './pages/Login'
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

export default function App() {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait" initial={false}>
      <Routes location={location} key={location.pathname}>
        <Route path="/login" element={<Login />} />
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
  )
}
