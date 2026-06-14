import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App'
import { authRoutes } from '@/features/auth/routes'

const AppRoutes = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        {authRoutes}
      </Routes>
    </BrowserRouter>
  )
}

export default AppRoutes
