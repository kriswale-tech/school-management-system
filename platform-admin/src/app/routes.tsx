import { useEffect, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import LoginPage from '@/features/auth/LoginPage'
import DashboardPage from '@/features/dashboard/DashboardPage'
import SchoolsPage from '@/features/schools/SchoolsPage'
import SchoolDetailPage from '@/features/schools/SchoolDetailPage'
import SettingsPage from '@/features/settings/SettingsPage'
import PlansPage from '@/features/billing/PlansPage'
import DiscountsPage from '@/features/billing/DiscountsPage'
import PaymentsPage from '@/features/billing/PaymentsPage'
import CurriculumPage from '@/features/curriculum/CurriculumPage'
import MessagesLayout from '@/features/messages/MessagesLayout'
import MessagesOverviewPage from '@/features/messages/OverviewPage'
import SmsPricingPage from '@/features/messages/SmsPricingPage'
import EmailPricingPage from '@/features/messages/EmailPricingPage'
import ProvidersPage from '@/features/messages/ProvidersPage'
import SchoolUsagePage from '@/features/messages/SchoolUsagePage'
import SchoolReportPage from '@/features/messages/SchoolReportPage'
import FreeSponsoredPage from '@/features/messages/FreeSponsoredPage'
import ProfitabilityPage from '@/features/messages/ProfitabilityPage'
import TransactionsPage from '@/features/messages/TransactionsPage'
import AppShell from '@/components/AppShell'
import { useAuthStore } from '@/features/auth/store'

function RequireAuth({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user)
  const bootstrapped = useAuthStore((s) => s.bootstrapped)

  if (!bootstrapped) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-[var(--color-ink)]/60">
        Loading…
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return children
}

export default function AppRoutes() {
  const bootstrap = useAuthStore((s) => s.bootstrap)

  useEffect(() => {
    void bootstrap()
  }, [bootstrap])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route path="/" element={<DashboardPage />} />
          <Route path="/schools" element={<SchoolsPage />} />
          <Route path="/schools/:id" element={<SchoolDetailPage />} />
          <Route path="/plans" element={<PlansPage />} />
          <Route path="/discounts" element={<DiscountsPage />} />
          <Route path="/payments" element={<PaymentsPage />} />
          <Route path="/curriculum" element={<CurriculumPage />} />
          <Route path="/messages" element={<MessagesLayout />}>
            <Route index element={<MessagesOverviewPage />} />
            <Route path="sms-pricing" element={<SmsPricingPage />} />
            <Route path="email-pricing" element={<EmailPricingPage />} />
            <Route path="providers" element={<ProvidersPage />} />
            <Route path="schools" element={<SchoolUsagePage />} />
            <Route path="schools/:id" element={<SchoolReportPage />} />
            <Route path="free-sponsored" element={<FreeSponsoredPage />} />
            <Route path="profitability" element={<ProfitabilityPage />} />
            <Route path="transactions" element={<TransactionsPage />} />
          </Route>
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
