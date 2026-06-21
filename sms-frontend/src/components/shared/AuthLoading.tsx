import AppLogo from './AppLogo'

const AuthLoading = () => {
  return (
    <div
      className="flex min-h-screen items-center justify-center bg-white"
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label="Loading"
    >
      <AppLogo className="animate-pulse" />
    </div>
  )
}

export default AuthLoading
