import { createContext } from 'react'

export type TransitionWizardContextValue = {
  openWizard: () => void
}

export const TransitionWizardContext = createContext<TransitionWizardContextValue | null>(null)
