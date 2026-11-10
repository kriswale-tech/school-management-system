import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import './index.css'
import AppShell from '@/components/AppShell'
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
import { useAuthStore } from '@/features/auth/store'

useAuthStore.setState({
  bootstrapped: true,
  user: {
    id: 'preview',
    email: 'preview@schoolasst.test',
    first_name: 'Preview',
    last_name: 'User',
    full_name: 'Preview User',
    role: 'super_admin',
    mfa_enabled: false,
    is_active: true,
    created_at: new Date().toISOString(),
  },
})

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
})

createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <MemoryRouter initialEntries={['/messages']}>
      <Routes>
        <Route element={<AppShell />}>
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
        </Route>
        <Route path="*" element={<Navigate to="/messages" replace />} />
      </Routes>
    </MemoryRouter>
    <Toaster position="top-right" />
  </QueryClientProvider>,
)
