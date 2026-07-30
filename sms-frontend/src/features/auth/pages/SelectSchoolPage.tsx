import { useEffect } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { SelectSchoolForm } from '../components'
import { getUser, selectSchool } from '../services'
import { useAuthStore } from '../store'
import { AuthLoading } from '@/components/shared'
import { getApiErrorMessage } from '@/utils'
import { getPostAuthPath } from '../utils'

const SelectSchoolPage = () => {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const setUser = useAuthStore((state) => state.setUser)

  const { data: me, isLoading, isError, error } = useQuery({
    queryKey: ['me', 'select-school'],
    queryFn: getUser,
  })

  useEffect(() => {
    if (me) setUser(me)
  }, [me, setUser])

  useEffect(() => {
    if (!isError) return
    toast.error(getApiErrorMessage(error, 'Unable to load your schools.'))
  }, [isError, error])

  useEffect(() => {
    if (!me || me.requires_school_selection) return
    if (me.schools.length !== 1) return
    navigate(getPostAuthPath(me), { replace: true })
  }, [me, navigate])

  const { mutate: selectSchoolMutation, isPending } = useMutation({
    mutationFn: async (schoolId: string) => {
      await selectSchool({ school_id: schoolId })
      return getUser()
    },
    onSuccess: (scopedUser) => {
      setUser(scopedUser)
      toast.success('School selected')
      navigate(getPostAuthPath(scopedUser), { replace: true })
    },
    onError: (mutationError) => {
      toast.error(getApiErrorMessage(mutationError, 'Unable to select school. Please try again.'))
    },
  })

  const schools = me?.schools ?? user?.schools ?? []
  const activeSchoolId = me?.school_id ?? user?.school_id
  const isSwitching = Boolean(activeSchoolId) && !(me?.requires_school_selection ?? user?.requires_school_selection)

  if (isLoading && schools.length === 0) {
    return <AuthLoading />
  }

  if (me && !me.requires_school_selection && me.schools.length === 1) {
    return <AuthLoading />
  }

  if (schools.length === 0) {
    return (
      <SelectSchoolForm
        schools={[]}
        onSelect={() => undefined}
        title="No schools available"
        description="Your account is not linked to any school. Contact your administrator for access."
      />
    )
  }

  return (
    <SelectSchoolForm
      schools={schools}
      activeSchoolId={activeSchoolId}
      onSelect={(schoolId) => selectSchoolMutation(schoolId)}
      isSubmitting={isPending}
      title={isSwitching ? 'Switch school' : 'Select a school'}
      description={
        isSwitching
          ? 'Choose another school to continue working in.'
          : 'You belong to more than one school. Choose which one to continue with.'
      }
    />
  )
}

export default SelectSchoolPage
