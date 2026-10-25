import { useEffect, useState } from 'react'
import { Icon } from '@iconify/react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useParams } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import StatsCard from '@/components/shared/StatsCard'
import { ConfirmDialog } from '@/components/shared'
import TabComponent from '@/components/shared/TabComponent'
import { Button } from '@/components/ui'
import { Capability } from '@/features/auth/capabilities'
import { useAccess, useCan } from '@/features/auth/hooks'
import { getApiErrorMessage } from '@/utils'
import SubjectPerformancePanel from '@/features/reports/components/SubjectPerformancePanel'
import AssignSubjectGroupStudents from '../components/AssignSubjectGroupStudents'
import ClassStudentsTable from '../components/ClassStudentsTable'
import PublishStudentsModal from '../components/PublishStudentsModal'
import SubjectAssessmentWorkspace from '../components/SubjectAssessmentWorkspace'
import {
  getTeachingAssignmentDetail,
  getTeachingAssignmentPerformance,
  getTeachingAssignmentStudents,
  getTeachingAssignmentWorkspace,
  publishTeachingAssignmentStudents,
  unassignSubjectGroupStudents,
} from '../services'
import type { ClassStudent } from '../types'

type DetailTab = 'Workspace' | 'Students' | 'Performance'

const SubjectDetail = () => {
  const { assignmentId } = useParams<{ assignmentId: string }>()
  const queryClient = useQueryClient()
  const access = useAccess()
  const canRecord = useCan(Capability.ASSESSMENTS_RECORD)
  // Workspace (marks / publish) is only for subject teachers — not admin or class-only.
  const showWorkspace = access.is_subject_teacher && canRecord

  const defaultTab: DetailTab = showWorkspace ? 'Workspace' : 'Students'
  const [activeTab, setActiveTab] = useState<DetailTab>(defaultTab)
  const [isRecording, setIsRecording] = useState(false)
  const [addCaOpen, setAddCaOpen] = useState(false)
  const [publishOpen, setPublishOpen] = useState(false)
  const [assignOpen, setAssignOpen] = useState(false)
  const [pendingUnassign, setPendingUnassign] = useState<ClassStudent | null>(null)

  useEffect(() => {
    if (!showWorkspace && activeTab === 'Workspace') {
      setActiveTab('Students')
    }
  }, [showWorkspace, activeTab])

  const {
    data: subject,
    isLoading: isLoadingDetail,
    isError,
    error,
  } = useQuery({
    queryKey: ['classes', 'teaching-assignment', assignmentId],
    queryFn: () => getTeachingAssignmentDetail(assignmentId!),
    enabled: Boolean(assignmentId),
  })

  const { data: studentsData, isLoading: isLoadingStudents } = useQuery({
    queryKey: ['classes', 'teaching-assignment', assignmentId, 'students'],
    queryFn: () => getTeachingAssignmentStudents(assignmentId!),
    enabled: Boolean(assignmentId),
  })

  const { data: workspace } = useQuery({
    queryKey: ['classes', 'teaching-assignment', assignmentId, 'workspace'],
    queryFn: () => getTeachingAssignmentWorkspace(assignmentId!),
    enabled: Boolean(assignmentId) && activeTab === 'Workspace' && showWorkspace,
  })

  const {
    data: performance,
    isLoading: isLoadingPerformance,
    isError: isPerformanceError,
    error: performanceError,
  } = useQuery({
    queryKey: ['classes', 'teaching-assignment', assignmentId, 'performance'],
    queryFn: () => getTeachingAssignmentPerformance(assignmentId!),
    enabled: Boolean(assignmentId) && activeTab === 'Performance',
  })

  const { mutate: publishStudents, isPending: isPublishing } = useMutation({
    mutationFn: (studentIds: string[]) =>
      publishTeachingAssignmentStudents(assignmentId!, studentIds),
    onSuccess: () => {
      toast.success('Results published to the class teacher')
      void queryClient.invalidateQueries({
        queryKey: ['classes', 'teaching-assignment', assignmentId, 'workspace'],
      })
      void queryClient.invalidateQueries({ queryKey: ['me', 'teaching'] })
      setPublishOpen(false)
    },
    onError: (err) => toast.error(getApiErrorMessage(err, 'Unable to publish results')),
  })

  const { mutate: unassignStudent, isPending: isUnassigning } = useMutation({
    mutationFn: (studentId: string) =>
      unassignSubjectGroupStudents(assignmentId!, [studentId]),
    onSuccess: () => {
      toast.success('Student unassigned from group')
      void queryClient.invalidateQueries({
        queryKey: ['classes', 'teaching-assignment', assignmentId],
      })
      setPendingUnassign(null)
    },
    onError: (err) => {
      toast.error(getApiErrorMessage(err, 'Unable to unassign student'))
    },
  })

  const isGrouped = Boolean(subject?.is_grouped)
  const unassignedCount = subject?.unassigned_students_count ?? 0
  const students = studentsData?.results ?? []

  const switchTab = (tab: DetailTab) => {
    setActiveTab(tab)
    if (tab !== 'Workspace') {
      setIsRecording(false)
      setAddCaOpen(false)
      setPublishOpen(false)
    }
  }

  const tabs: Array<{ label: DetailTab; onClick: () => void }> = []
  if (showWorkspace) {
    tabs.push({ label: 'Workspace', onClick: () => switchTab('Workspace') })
  }
  tabs.push(
    { label: 'Students', onClick: () => switchTab('Students') },
    { label: 'Performance', onClick: () => switchTab('Performance') },
  )

  return (
    <div className="space-y-6">
      <ActionBar title="Subject Detail" back={true} />

      {isLoadingDetail ? (
        <p className="text-sm text-slate-500">Loading subject details…</p>
      ) : isError || !subject ? (
        <p className="text-sm text-red-600" role="alert">
          {getApiErrorMessage(error, 'Unable to load subject details.')}
        </p>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatsCard title="Class" value={subject.class_level_name} />
            <StatsCard title="Stream" value={subject.stream_name ?? '—'} />
            <StatsCard
              title="Students"
              value={String(subject.students_count)}
            />
            <StatsCard title="Subject" value={subject.subject_label} />
          </div>

          <div className="bg-white p-4 custom-shadow-md space-y-6">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <TabComponent tabs={tabs} activeTab={activeTab} />

              {activeTab === 'Students' && isGrouped && assignmentId ? (
                <Button
                  type="button"
                  className="max-w-fit py-2 text-sm"
                  onClick={() => setAssignOpen(true)}
                >
                  <Icon
                    icon="hugeicons:plus-sign"
                    className="size-4 bg-white text-black rounded-full p-0.5"
                  />
                  Assign students
                </Button>
              ) : null}
            </div>

            {activeTab === 'Students' && isGrouped && unassignedCount > 0 ? (
              <div
                className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
                role="status"
              >
                {unassignedCount}{' '}
                {unassignedCount === 1 ? 'student is' : 'students are'} not in any{' '}
                {subject.subject_name} group yet. Assign unassigned students to this group, or ask
                another group teacher to unassign first if they are already placed.
              </div>
            ) : null}

            {activeTab === 'Workspace' && showWorkspace ? (
              assignmentId ? (
                <SubjectAssessmentWorkspace
                  key={isRecording ? `recording-${assignmentId}` : `view-${assignmentId}`}
                  assignmentId={assignmentId}
                  canRecord={canRecord}
                  isRecording={isRecording}
                  onExitRecording={() => {
                    setIsRecording(false)
                    setAddCaOpen(false)
                  }}
                  onStartRecording={() => setIsRecording(true)}
                  onPublish={() => setPublishOpen(true)}
                  onOpenAddCa={() => setAddCaOpen(true)}
                  addCaOpen={addCaOpen}
                  onCloseAddCa={() => setAddCaOpen(false)}
                />
              ) : null
            ) : activeTab === 'Students' ? (
              <ClassStudentsTable
                students={students}
                isLoading={isLoadingStudents}
                onUnassignStudent={
                  isGrouped
                    ? (student) => {
                        setPendingUnassign(student)
                      }
                    : undefined
                }
              />
            ) : isLoadingPerformance ? (
              <p className="text-sm text-slate-500 py-8">Loading performance…</p>
            ) : isPerformanceError || !performance ? (
              <p className="text-sm text-red-600 py-8" role="alert">
                {getApiErrorMessage(
                  performanceError,
                  'Unable to load subject performance.',
                )}
              </p>
            ) : (
              <SubjectPerformancePanel data={performance} />
            )}
          </div>
        </>
      )}

      <PublishStudentsModal
        open={publishOpen}
        students={workspace?.students ?? []}
        isPublishing={isPublishing}
        onClose={() => setPublishOpen(false)}
        onPublish={(studentIds) => publishStudents(studentIds)}
      />

      {assignmentId && subject?.is_grouped && subject.subject_group_name ? (
        <AssignSubjectGroupStudents
          open={assignOpen}
          assignmentId={assignmentId}
          groupName={subject.subject_group_name}
          onClose={() => setAssignOpen(false)}
        />
      ) : null}

      <ConfirmDialog
        open={Boolean(pendingUnassign)}
        title="Unassign student"
        message={
          pendingUnassign
            ? `Remove ${pendingUnassign.full_name} from this subject group? They will become unassigned until another teacher adds them.`
            : ''
        }
        confirmLabel="Unassign"
        onClose={() => setPendingUnassign(null)}
        onConfirm={() => {
          if (!pendingUnassign) return
          unassignStudent(pendingUnassign.id)
        }}
        isLoading={isUnassigning}
      />
    </div>
  )
}

export default SubjectDetail
