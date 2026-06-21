import { Toaster } from 'react-hot-toast'

const AppToaster = () => {
  return (
    <Toaster
      position="top-center"
      toastOptions={{
        duration: 4000,
        className: 'text-sm',
        style: {
          fontFamily: 'var(--font-poppins)',
        },
        success: {
          iconTheme: {
            primary: '#0f172a',
            secondary: '#ffffff',
          },
        },
        error: {
          iconTheme: {
            primary: '#dc2626',
            secondary: '#ffffff',
          },
        },
      }}
    />
  )
}

export default AppToaster
