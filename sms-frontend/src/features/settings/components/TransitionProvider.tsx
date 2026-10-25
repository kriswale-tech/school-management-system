import { useState, type ReactNode } from 'react'
import { TransitionWizardContext } from './transitionWizardContext'
import TransitionWizard from './TransitionWizard'

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
