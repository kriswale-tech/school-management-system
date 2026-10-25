import { useMemo, useState } from 'react'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import ClassPerformancePanel from './ClassPerformancePanel'
import SubjectPerformancePanel from './SubjectPerformancePanel'
import type { TeacherDeskClass, TeacherDeskResponse, TeacherDeskSubject } from '../types'

export type TeacherDeskMode = 'classes' | 'subjects'

type TeacherDeskTabProps = {
  data?: TeacherDeskResponse
  mode: TeacherDeskMode
}

const ClassesDesk = ({ classes }: { classes: TeacherDeskClass[] }) => {
  const [classKey, setClassKey] = useState<FilterSelection>('')

  const options = useMemo(
    () =>
      classes.map((row) => ({
        value: `${row.class_level_id}:${row.stream_id ?? 'all'}`,
        label: row.display_name,
      })),
    [classes],
  )

  const resolvedClassKey = options.some((option) => option.value === String(classKey))
    ? String(classKey)
    : (options[0]?.value ?? '')

  const selected = useMemo(() => {
    return (
      classes.find(
        (row) => `${row.class_level_id}:${row.stream_id ?? 'all'}` === resolvedClassKey,
      ) ?? classes[0]
    )
  }, [classes, resolvedClassKey])

  if (!selected) {
    return (
      <div className="bg-white p-8 custom-shadow-md text-sm text-slate-600">
        No class teacher assignments for this term.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <FilterComponent
          filterName="Class"
          filterKey="teacher-desk-class"
          options={options}
          value={resolvedClassKey}
          allowEmpty={false}
          onChange={setClassKey}
          className="min-w-56"
        />
      </div>
      <ClassPerformancePanel data={selected} />
    </div>
  )
}

const SubjectsDesk = ({ subjects }: { subjects: TeacherDeskSubject[] }) => {
  const [classFilter, setClassFilter] = useState<FilterSelection>('')
  const [subjectKey, setSubjectKey] = useState<FilterSelection>('')

  const classOptions = useMemo(() => {
    const seen = new Map<string, string>()
    for (const row of subjects) {
      const key = `${row.class_level_id}:${row.stream_id ?? 'all'}`
      if (!seen.has(key)) {
        const label = row.display_name.includes(' · ')
          ? row.display_name.split(' · ').slice(1).join(' · ')
          : row.display_name
        seen.set(key, label)
      }
    }
    return Array.from(seen.entries()).map(([value, label]) => ({ value, label }))
  }, [subjects])

  const filteredSubjects = useMemo(() => {
    if (classFilter === '') return subjects
    return subjects.filter(
      (row) => `${row.class_level_id}:${row.stream_id ?? 'all'}` === String(classFilter),
    )
  }, [subjects, classFilter])

  const subjectOptions = useMemo(
    () =>
      filteredSubjects.map((row) => ({
        value: row.teaching_assignment_id,
        label: row.subject_name,
      })),
    [filteredSubjects],
  )

  const resolvedSubjectKey = subjectOptions.some(
    (option) => option.value === String(subjectKey),
  )
    ? String(subjectKey)
    : (subjectOptions[0]?.value ?? '')

  const selected = useMemo(() => {
    return (
      filteredSubjects.find((row) => row.teaching_assignment_id === resolvedSubjectKey) ??
      filteredSubjects[0]
    )
  }, [filteredSubjects, resolvedSubjectKey])

  if (subjects.length === 0) {
    return (
      <div className="bg-white p-8 custom-shadow-md text-sm text-slate-600">
        No subject teaching assignments for this term.
      </div>
    )
  }

  if (!selected) {
    return (
      <div className="bg-white p-8 custom-shadow-md text-sm text-slate-600">
        No subjects match this class filter.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        {classOptions.length > 1 ? (
          <FilterComponent
            filterName="Class"
            filterKey="teacher-desk-subject-class"
            options={classOptions}
            value={classFilter}
            placeholder="All classes"
            onChange={(value) => {
              setClassFilter(value)
              setSubjectKey('')
            }}
            className="min-w-48"
          />
        ) : null}
        <FilterComponent
          filterName="Subject"
          filterKey="teacher-desk-subject"
          options={subjectOptions}
          value={resolvedSubjectKey}
          allowEmpty={false}
          onChange={setSubjectKey}
          className="min-w-48"
        />
        <p className="pb-2 text-sm text-slate-500">
          {selected.display_name} · {selected.students_count} students
        </p>
      </div>
      <SubjectPerformancePanel data={selected} />
    </div>
  )
}

const TeacherDeskTab = ({ data, mode }: TeacherDeskTabProps) => {
  if (!data) {
    return (
      <div className="bg-white p-8 custom-shadow-md text-sm text-slate-500">
        Loading…
      </div>
    )
  }

  if (mode === 'classes') {
    return <ClassesDesk classes={data.classes} />
  }

  return <SubjectsDesk subjects={data.subjects} />
}

export default TeacherDeskTab
