import api from '@/app/api/api'
import type {
  ByClassResponse,
  BySubjectResponse,
  EnrollmentResponse,
  FeesAcademicRiskResponse,
  FinanceResponse,
  GradeDistributionResponse,
  ReportsFilterOptions,
  ReportsOverview,
  ReportsQueryParams,
  StaffCapacityResponse,
  StudentTrendsResponse,
  SubjectHeatmapResponse,
  TeacherDeskResponse,
  WorkflowResponse,
} from './types'

const withParams = (params?: ReportsQueryParams) => {
  if (!params) return undefined
  const cleaned: Record<string, string | number> = {}
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    cleaned[key] = value
  }
  return cleaned
}

export const getReportsFilterOptions = async (): Promise<ReportsFilterOptions> => {
  const response = await api.get<ReportsFilterOptions>('/reports/filters/')
  return response.data
}

export const getReportsOverview = async (
  params?: ReportsQueryParams,
): Promise<ReportsOverview> => {
  const response = await api.get<ReportsOverview>('/reports/overview/', {
    params: withParams(params),
  })
  return response.data
}

export const getReportsByClass = async (
  params?: ReportsQueryParams,
): Promise<ByClassResponse> => {
  const response = await api.get<ByClassResponse>('/reports/by-class/', {
    params: withParams(params),
  })
  return response.data
}

export const getReportsBySubject = async (
  params?: ReportsQueryParams,
): Promise<BySubjectResponse> => {
  const response = await api.get<BySubjectResponse>('/reports/by-subject/', {
    params: withParams(params),
  })
  return response.data
}

export const getReportsGradeDistribution = async (
  params?: ReportsQueryParams,
): Promise<GradeDistributionResponse> => {
  const response = await api.get<GradeDistributionResponse>('/reports/grade-distribution/', {
    params: withParams(params),
  })
  return response.data
}

export const getReportsStudentTrends = async (
  params?: ReportsQueryParams,
): Promise<StudentTrendsResponse> => {
  const response = await api.get<StudentTrendsResponse>('/reports/student-trends/', {
    params: withParams(params),
  })
  return response.data
}

export const getReportsSubjectHeatmap = async (
  params?: ReportsQueryParams,
): Promise<SubjectHeatmapResponse> => {
  const response = await api.get<SubjectHeatmapResponse>('/reports/subject-heatmap/', {
    params: withParams(params),
  })
  return response.data
}

export const getReportsWorkflow = async (
  params?: ReportsQueryParams,
): Promise<WorkflowResponse> => {
  const response = await api.get<WorkflowResponse>('/reports/workflow/', {
    params: withParams(params),
  })
  return response.data
}

export const getReportsFeesAcademicRisk = async (
  params?: ReportsQueryParams,
): Promise<FeesAcademicRiskResponse> => {
  const response = await api.get<FeesAcademicRiskResponse>('/reports/fees-academic-risk/', {
    params: withParams(params),
  })
  return response.data
}

export const getReportsFinance = async (
  params?: ReportsQueryParams,
): Promise<FinanceResponse> => {
  const response = await api.get<FinanceResponse>('/reports/finance/', {
    params: withParams(params),
  })
  return response.data
}

export const getReportsEnrollment = async (
  params?: ReportsQueryParams,
): Promise<EnrollmentResponse> => {
  const response = await api.get<EnrollmentResponse>('/reports/enrollment/', {
    params: withParams(params),
  })
  return response.data
}

export const getReportsStaffCapacity = async (
  params?: ReportsQueryParams,
): Promise<StaffCapacityResponse> => {
  const response = await api.get<StaffCapacityResponse>('/reports/staff-capacity/', {
    params: withParams(params),
  })
  return response.data
}

export const getReportsTeacherDesk = async (
  params?: ReportsQueryParams,
): Promise<TeacherDeskResponse> => {
  const response = await api.get<TeacherDeskResponse>('/reports/teacher-desk/', {
    params: withParams(params),
  })
  return response.data
}
