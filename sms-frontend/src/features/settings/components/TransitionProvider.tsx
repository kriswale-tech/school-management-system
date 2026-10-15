import { createContext, useContext, useState, type ReactNode } from 'react'
import TransitionWizard from './TransitionWizard'

type TransitionWizardContextValue = {
  openWizard: () => void
}

const TransitionWizardContext = createContext<TransitionWizardContextValue | null>(null)

export const useTransitionWizard = () => {
  return useContext(TransitionWizardContext)
}

const TransitionProvider = ({ children }: { children: ReactNode }) => {
  const [wizardOpen, setWizardOpen] = useState(false)

  return (
    <TransitionWizardContext.Provider value={{ openWizard: () => setWizardOpen(true) }}>
      {children}
      <TransitionWizard open={wizardOpen} onClose={() => setWizardOpen(false)} />
    </TransitionWizardContext.Provider>
  )
}

export default TransitionProvider
