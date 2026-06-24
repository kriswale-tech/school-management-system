import { useParams } from 'react-router-dom'
import AcademicYear from './AcademicYear'
import Classes from './Classes'
import Fees from './Fees'
import Review from './Review'
import SchoolProfile from './SchoolProfile'
import Staff from './Staff'

const stepPages = {
  school_profile: SchoolProfile,
  academic_year: AcademicYear,
  classes: Classes,
  staff: Staff,
  fees: Fees,
  review: Review,
} as const

const SetupStepPage = () => {
  const { step } = useParams<{ step: string }>()
  const Page = step && step in stepPages ? stepPages[step as keyof typeof stepPages] : null

  if (Page) {
    return <Page />
  }

  return <div>{step?.replace(/_/g, ' ') ?? 'Setup'}</div>
}

export default SetupStepPage
