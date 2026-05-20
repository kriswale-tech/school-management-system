import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App'
import { authRoutes } from '@/features/auth/routes'
import { Suspense } from 'react'

const AppRoutes = () => {
  return (
    <BrowserRouter>
      <Suspense fallback={<div>Loading...</div>}>
        <Routes>
          <Route path="/" element={<App />} />
          {authRoutes}
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

export default AppRoutes
