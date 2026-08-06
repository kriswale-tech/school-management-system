import ActionBar from '@/components/shared/ActionBar'
import TabComponent from '@/components/shared/TabComponent'
import { DotComponent } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { Icon } from '@iconify/react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import AssignClassTeacher from '../components/AssignClassTeacher'
import ClassStudentsTable from '../components/ClassStudentsTable'
import ClassSubjectsTable from '../components/ClassSubjectsTable'
import { getClassDetail, getClassStudents, getClassSubjects } from '../services'

const TAB_STUDENTS = 'Students'
const TAB_SUBJECTS = 'Subjects'

const ClassDetail = () => {
  const { id: streamId } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState(TAB_STUDENTS)
  const [assignClassTeacherOpen, setAssignClassTeacherOpen] = useState(false)

  const {
    data: classDetail,
    isLoading: isLoadingDetail,
    isError,
    error,
  } = useQuery({
    queryKey: ['classes', 'detail', streamId],
    queryFn: () => getClassDetail(streamId!),
    enabled: Boolean(streamId),
  })

  const { data: studentsData, isLoading: isLoadingStudents } = useQuery({
    queryKey: ['classes', 'students', streamId],
    queryFn: () => getClassStudents(streamId!),
    enabled: Boolean(streamId) && activeTab === TAB_STUDENTS,
  })

  const { data: subjectsData, isLoading: isLoadingSubjects } = useQuery({
    queryKey: ['classes', 'subjects', streamId],
    queryFn: () => getClassSubjects(streamId!),
    enabled: Boolean(streamId) && activeTab === TAB_SUBJECTS,
  })

  const tabs = [
    {
      label: TAB_STUDENTS,
      onClick: () => setActiveTab(TAB_STUDENTS),
    },
    {
      label: TAB_SUBJECTS,
      onClick: () => setActiveTab(TAB_SUBJECTS),
      attention: Boolean(classDetail?.needs_attention),
    },
  ]

  const invalidateClassQueries = () => {
    void queryClient.invalidateQueries({ queryKey: ['classes', 'detail', streamId] })
    void queryClient.invalidateQueries({ queryKey: ['classes', 'subjects', streamId] })
    void queryClient.invalidateQueries({ queryKey: ['classes', 'list'] })
    void queryClient.invalidateQueries({ queryKey: ['classes', 'stats'] })
    void queryClient.invalidateQueries({ queryKey: ['classes', 'teachers'] })
  }

  return (
    <div className="space-y-6">
      <ActionBar title="Class Detail" back={true} />

      <div className="bg-white p-4 custom-shadow-md">
        {isLoadingDetail ? (
          <p className="text-sm text-slate-500 py-8">Loading class details…</p>
        ) : isError || !classDetail ? (
          <p className="text-sm text-red-600 py-8" role="alert">
            {getApiErrorMessage(error, 'Unable to load class details.')}
          </p>
        ) : (
          <>
            <h2 className="text-2xl font-medium mb-1">{classDetail.name}</h2>

            <div className="flex flex-wrap items-center gap-x-0">
              <span className="text-sm text-gray-500">{classDetail.level_name}</span>
              <DotComponent />
              <span className="text-sm text-gray-500">
                {classDetail.students_count}{' '}
                {classDetail.students_count === 1 ? 'student' : 'students'}
              </span>
              <DotComponent />
              {classDetail.class_teacher ? (
                <button
                  type="button"
                  className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-slate-700 cursor-pointer"
                  onClick={() => setAssignClassTeacherOpen(true)}
                >
                  {classDetail.class_teacher.full_name} (Class Teacher)
                  <Icon icon="hugeicons:pencil-edit-02" className="size-4" />
                </button>
              ) : (
                <button
                  type="button"
                  className="text-sm text-red-600 cursor-pointer"
                  onClick={() => setAssignClassTeacherOpen(true)}
                >
                  Assign Class Teacher
                </button>
              )}
            </div>

            <div className="mt-10">
              <TabComponent tabs={tabs} activeTab={activeTab} />
            </div>

            <div className="mt-10">
              {activeTab === TAB_STUDENTS && (
                <ClassStudentsTable
                  students={studentsData?.results ?? []}
                  isLoading={isLoadingStudents}
                />
              )}
              {activeTab === TAB_SUBJECTS && streamId && (
                <ClassSubjectsTable
                  streamId={streamId}
                  subjects={subjectsData?.results ?? []}
                  isLoading={isLoadingSubjects}
                  onAssigned={invalidateClassQueries}
                />
              )}
            </div>
          </>
        )}
      </div>

      {streamId && classDetail ? (
        <AssignClassTeacher
          open={assignClassTeacherOpen}
          streamId={streamId}
          classDisplayName={classDetail.name}
          selectedTeacherId={classDetail.class_teacher?.id ?? null}
          onClose={() => setAssignClassTeacherOpen(false)}
          onAssigned={invalidateClassQueries}
        />
      ) : null}
    </div>
  )
}

export default ClassDetail
