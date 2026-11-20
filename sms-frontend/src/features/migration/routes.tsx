import { lazy } from 'react'
import { Route } from 'react-router-dom'

const MigrationShell = lazy(() => import('./components/MigrationShell'))
const MigrationHome = lazy(() => import('./pages/MigrationHome'))
const MigrationUpload = lazy(() => import('./pages/MigrationUpload'))
const MigrationMap = lazy(() => import('./pages/MigrationMap'))
const MigrationValues = lazy(() => import('./pages/MigrationValues'))
const MigrationMatch = lazy(() => import('./pages/MigrationMatch'))
const MigrationEnrollments = lazy(() => import('./pages/MigrationEnrollments'))
const MigrationSummary = lazy(() => import('./pages/MigrationSummary'))
const MigrationCommit = lazy(() => import('./pages/MigrationCommit'))
const MigrationProgress = lazy(() => import('./pages/MigrationProgress'))

export const migrationRoutes = (
  <Route path="migration" element={<MigrationShell />}>
    <Route index element={<MigrationHome />} />
    <Route path=":jobId/upload" element={<MigrationUpload />} />
    <Route path=":jobId/map" element={<MigrationMap />} />
    <Route path=":jobId/values" element={<MigrationValues />} />
    <Route path=":jobId/match" element={<MigrationMatch />} />
    <Route path=":jobId/enrollments" element={<MigrationEnrollments />} />
    <Route path=":jobId/summary" element={<MigrationSummary />} />
    <Route path=":jobId/commit" element={<MigrationCommit />} />
    <Route path=":jobId/progress" element={<MigrationProgress />} />
  </Route>
)
