import type { ComponentType } from 'react'
import { useOutletContext, useParams } from 'react-router-dom'
import type { Setup } from '../types'
import AcademicYearAndTerm from './AcademicYearAndTerm'
import Assessment from './Assessment'
import ClassesAndSubjects from './ClassesAndSubjects'
import Fees from './Fees'
import SchoolProfile from './SchoolProfile'
import Staff from './Staff'
import Teachers from './Teachers'

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
