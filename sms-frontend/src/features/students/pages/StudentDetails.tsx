import { useParams, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import ActionBar from '@/components/shared/ActionBar'
import { TabComponent } from '@/components/shared'
import { AvatarComponent } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import Assessment from '../components/detail-pages/Assessment'
import Bio from '../components/detail-pages/Bio'
import Fees from '../components/detail-pages/Fees'
import Guardian from '../components/detail-pages/Guardian'
import Performance from '../components/detail-pages/Performance'
import { getStudent } from '../services'
import { STUDENT_DETAIL_QUERY_KEY } from '../utils'
import DotComponent from '@/components/ui/DotComponent'

const TAB_BIO = 'Bio'
const TAB_GUARDIAN = 'Guardian'
const TAB_PERFORMANCE = 'Performance'
const TAB_ASSESSMENT = 'Reports & Assessment'
const TAB_FEES = 'Fees'

const TAB_FROM_QUERY: Record<string, string> = {
  bio: TAB_BIO,
  guardian: TAB_GUARDIAN,
  performance: TAB_PERFORMANCE,
  assessment: TAB_ASSESSMENT,
  fees: TAB_FEES,
}

const QUERY_FROM_TAB: Record<string, string> = {
  [TAB_BIO]: 'bio',
  [TAB_GUARDIAN]: 'guardian',
  [TAB_PERFORMANCE]: 'performance',
  [TAB_ASSESSMENT]: 'assessment',
  [TAB_FEES]: 'fees',
}

const StudentDetails = () => {
  const { id } = useParams<{ id: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab')
  const activeTab =
    (tabParam && TAB_FROM_QUERY[tabParam.toLowerCase()]) || TAB_BIO

  const selectTab = (label: string) => {
    const key = QUERY_FROM_TAB[label]
    if (!key) return
    const next = new URLSearchParams(searchParams)
    if (key === 'bio') {
      next.delete('tab')
      next.delete('feesTab')
    } else {
      next.set('tab', key)
      if (key !== 'fees') next.delete('feesTab')
    }
    setSearchParams(next, { replace: true })
  }

  const {
    data: student,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: [STUDENT_DETAIL_QUERY_KEY, id],
    queryFn: () => getStudent(id!),
    enabled: Boolean(id),
  })

  const tabs = [
    {
      label: TAB_BIO,
      onClick: () => selectTab(TAB_BIO),
    },
    {
      label: TAB_GUARDIAN,
      onClick: () => selectTab(TAB_GUARDIAN),
    },
    {
      label: TAB_PERFORMANCE,
      onClick: () => selectTab(TAB_PERFORMANCE),
    },
    {
      label: TAB_ASSESSMENT,
      onClick: () => selectTab(TAB_ASSESSMENT),
    },
    {
      label: TAB_FEES,
      onClick: () => selectTab(TAB_FEES),
    },
  ]

  return (
    <div className="space-y-6">
      <ActionBar back title="Student Details" />

      <div className="bg-white p-4 custom-shadow-md">
        {isLoading ? (
          <p className="text-sm text-slate-500 py-8">Loading student details…</p>
        ) : isError || !student ? (
          <p className="text-sm text-red-600 py-8" role="alert">
            {getApiErrorMessage(error, 'Unable to load student details.')}
          </p>
        ) : (
          <>
            <div className="flex items-center gap-4 mb-6">
              <AvatarComponent fullName={student.full_name} size={100} />
              <div>
                <h2 className="text-2xl font-medium mb-1">{student.full_name}</h2>
                <span className="text-sm text-gray-500">#{student.student_id}</span>
                {student.class_assignment ? (
                  <>
                    <DotComponent />
                    <span className="text-sm text-gray-500">
                      {student.class_assignment.display_name}
                    </span>
                  </>
                ) : null}
                <DotComponent />
                <span
                  className={
                    student.is_active ? 'text-sm text-green-600' : 'text-sm text-slate-500'
                  }
                >
                  {student.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>

            <TabComponent tabs={tabs} activeTab={activeTab} />

            <div className="mt-4">
              {activeTab === TAB_BIO && <Bio student={student} />}
              {activeTab === TAB_GUARDIAN && (
                <Guardian studentId={student.id} guardians={student.guardians} />
              )}
              {activeTab === TAB_PERFORMANCE && <Performance studentId={student.id} />}
              {activeTab === TAB_ASSESSMENT && <Assessment studentId={student.id} />}
              {activeTab === TAB_FEES && <Fees studentId={student.id} />}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default StudentDetails
