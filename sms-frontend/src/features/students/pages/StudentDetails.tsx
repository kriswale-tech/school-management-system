import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import ActionBar from '@/components/shared/ActionBar'
import { TabComponent } from '@/components/shared'
import { AvatarComponent } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import Assessment from '../components/detail-pages/Assessment'
import Bio from '../components/detail-pages/Bio'
import Fees from '../components/detail-pages/Fees'
import Guardian from '../components/detail-pages/Guardian'
import { getStudent } from '../services'
import { STUDENT_DETAIL_QUERY_KEY } from '../utils'

const TAB_BIO = 'Bio'
const TAB_GUARDIAN = 'Guardian'
const TAB_ASSESSMENT = 'Reports & Assessment'
const TAB_FEES = 'Fees'

const StudentDetails = () => {
  const { id } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState(TAB_BIO)

  const { data: student, isLoading, isError, error } = useQuery({
    queryKey: [STUDENT_DETAIL_QUERY_KEY, id],
    queryFn: () => getStudent(id!),
    enabled: Boolean(id),
  })

  const tabs = [
    {
      label: TAB_BIO,
      onClick: () => setActiveTab(TAB_BIO),
    },
    {
      label: TAB_GUARDIAN,
      onClick: () => setActiveTab(TAB_GUARDIAN),
    },
    {
      label: TAB_ASSESSMENT,
      onClick: () => setActiveTab(TAB_ASSESSMENT),
    },
    {
      label: TAB_FEES,
      onClick: () => setActiveTab(TAB_FEES),
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
                    <span className="inline-block size-1 align-middle rounded-full bg-slate-800 mx-4" />
                    <span className="text-sm text-gray-500">
                      {student.class_assignment.display_name}
                    </span>
                  </>
                ) : null}
                <span className="inline-block size-1 align-middle rounded-full bg-slate-800 mx-4" />
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
              {activeTab === TAB_ASSESSMENT && <Assessment />}
              {activeTab === TAB_FEES && <Fees studentId={student.id} />}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default StudentDetails
