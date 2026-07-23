import toast from 'react-hot-toast'
import { Icon } from '@iconify/react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '@/components/ui/Button'
import { useAuthStore } from '@/features/auth/store'
import { handleSetupProgressResponse } from '@/features/setup/utils/handle-setup-progress-response'
import { getApiErrorMessage } from '@/utils'
import AddTeacherModal from './components/AddTeacherModal'
import TeacherTable from './components/TeacherTable'
import { completeTeacherSetup, getTeachers } from './services'

const Teachers = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setUser = useAuthStore((state) => state.setUser)
  const user = useAuthStore((state) => state.user)
  const [page, setPage] = useState(1)
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [addModalSession, setAddModalSession] = useState(0)

  const { data, isLoading } = useQuery({
    queryKey: ['teachers', page],
    queryFn: () => getTeachers(page),
  })

  const { mutate: completeSetup, isPending: isCompleting } = useMutation({
    mutationFn: completeTeacherSetup,
    onSuccess: (response) => {
      toast.success('Teachers setup saved')
      void queryClient.invalidateQueries({ queryKey: ['setup'] })
      void queryClient.invalidateQueries({ queryKey: ['teachers'] })
      handleSetupProgressResponse(response, { navigate, user, setUser })
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to complete teachers setup'))
    },
  })

  const openAddModal = () => {
    setAddModalSession((session) => session + 1)
    setIsAddModalOpen(true)
  }
  const closeAddModal = () => setIsAddModalOpen(false)

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <div className="flex justify-between gap-2 items-end">
          <div>
            <h2 className="text-lg text-slate-900">Teachers</h2>
            <p className="text-sm text-slate-500 mt-1">Add and manage teachers for your school.</p>
          </div>

          <div className="flex items-center gap-2">
            <Button type="button" variant="ghost">
              <Icon icon="hugeicons:upload-01" className="size-4" />
              <span className="break-keep whitespace-nowrap">Bulk Upload Teachers</span>
            </Button>
            <Button type="button" onClick={openAddModal}>
              <Icon
                icon="hugeicons:plus-sign"
                className="size-4 bg-white text-black rounded-full p-0.5"
              />
              <span>Add Teacher</span>
            </Button>
          </div>
        </div>
      </div>

      <TeacherTable
        teachers={data?.results ?? []}
        isLoading={isLoading}
        pagination={data ?? null}
        onPageChange={setPage}
        onAddTeacher={openAddModal}
      />

      <Button
        type="button"
        variant="outline"
        onClick={() => completeSetup()}
        loading={isCompleting}
      >
        Proceed to Next Step
      </Button>

      <AddTeacherModal
        open={isAddModalOpen}
        onClose={closeAddModal}
        sessionKey={addModalSession}
      />
    </div>
  )
}

export default Teachers
