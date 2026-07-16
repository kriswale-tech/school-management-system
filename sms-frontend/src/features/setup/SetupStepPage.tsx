import type { ComponentType } from 'react'
import { useOutletContext, useParams } from 'react-router-dom'
import type { Setup } from './types/types'
import AcademicYearAndTerm from './academic-year-and-term/AcademicYearAndTerm'
import Assessment from './assessment/Assessment'
import ClassesAndSubjects from './classes-and-subjects/ClassesAndSubjects'
import Fees from './fees/Fees'
import SchoolProfile from './school-profile/SchoolProfile'
import Staff from './staff/Staff'
import Teachers from './teachers/Teachers'

/** Maps a backend step slug to its page component when one exists. */
const stepComponents: Record<string, ComponentType> = {
  school_profile: SchoolProfile,
  academic_year_term: AcademicYearAndTerm,
  classes_and_subjects: ClassesAndSubjects,
  assessment: Assessment,
  fees: Fees,
  teachers: Teachers,
  staff: Staff,
}

const SetupStepPage = () => {
  const setup = useOutletContext<Setup>()
  const { step } = useParams<{ step: string }>()

  const stepMeta = setup.steps.find((item) => item.step === step)
  const Page = step ? stepComponents[step] : undefined

  if (Page && stepMeta) {
    return <Page />
  }

  return <div>{stepMeta?.name ?? step?.replace(/_/g, ' ') ?? 'Setup'}</div>
}

export default SetupStepPage
