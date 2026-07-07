import { useQuery } from '@tanstack/react-query'
import ClassSubjectForm from '@/features/setup/components/class-and-subjects/ClassSubjectForm'
import { getClassAndSubjects } from '@/features/setup/services'
import LoadingSpinner from '@/components/ui/LoadingSpinner'

const ClassesAndSubjects = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['classAndSubjects'],
    queryFn: getClassAndSubjects,
  })

  if (isLoading) return <LoadingSpinner className="mx-auto" />

  return <ClassSubjectForm levels={data ?? []} />
}

export default ClassesAndSubjects
