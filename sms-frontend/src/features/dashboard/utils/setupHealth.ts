import type { AdminDashboardSetupHealth, AdminDashboardSetupHealthMetric } from '../types'

export const getSetupHealthMetrics = (
  health: AdminDashboardSetupHealth,
): AdminDashboardSetupHealthMetric[] => {
  const metrics = [
    health.class_teachers,
    health.subject_teachers,
    health.classes_with_students,
    health.subject_groups_with_students,
    health.students_in_subject_groups,
  ]
  return metrics.filter((metric) => {
    if (
      metric === health.subject_groups_with_students ||
      metric === health.students_in_subject_groups
    ) {
      return metric.total > 0
    }
    return true
  })
}

/** True when any applicable coverage bar is incomplete. */
export const isSetupHealthIncomplete = (health: AdminDashboardSetupHealth) =>
  getSetupHealthMetrics(health).some((metric) => metric.percent < 100)
