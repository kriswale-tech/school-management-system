import { useContext } from 'react'
import { TransitionWizardContext } from '../components/transitionWizardContext'

export const useTransitionWizard = () => {
  return useContext(TransitionWizardContext)
}
