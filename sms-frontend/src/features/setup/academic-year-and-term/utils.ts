import type {
  AcademicYearAndTerm,
  AcademicYearAndTermFormData,
  AcademicYearAndTermPayload,
  TermApiKey,
  TermName,
} from './types'

export const TERMS = ['First term', 'Second term', 'Third term'] as const

export const NUMBER_OF_TERMS = TERMS.length

const TERM_NAME_TO_API: Record<TermName, TermApiKey> = {
  'First term': 'first_term',
  'Second term': 'second_term',
  'Third term': 'third_term',
}

const TERM_API_TO_NAME: Record<TermApiKey, TermName> = {
  first_term: 'First term',
  second_term: 'Second term',
  third_term: 'Third term',
}

export const TERM_OPTIONS = TERMS.map((term) => ({ value: term, label: term }))

export const getAcademicYearOptions = (offset: number = 5) => {
  const currentYear = new Date().getFullYear()
  const startYear = currentYear - offset
  const endYear = currentYear + offset
  const options = []

  for (let year = startYear; year <= endYear; year++) {
    options.push({ value: `${year}/${year + 1}`, label: `${year}/${year + 1}` })
  }

  return options
}

export const getCurrentAcademicYear = () => {
  const currentYear = new Date().getFullYear()
  return `${currentYear}/${currentYear + 1}`
}

function toDateString(date: Date) {
  return date.toISOString().slice(0, 10)
}

function defaultTerms(): AcademicYearAndTermFormData['terms'] {
  return TERMS.map((name) => ({
    name,
    start_date: '',
    end_date: '',
  }))
}

/** Guesses the current term from scheduled dates relative to today. */
export function guessCurrentTerm(
  terms: Pick<AcademicYearAndTermFormData['terms'][number], 'start_date' | 'end_date'>[],
  referenceDate: Date = new Date(),
): TermName {
  const today = toDateString(referenceDate)

  for (let index = 0; index < TERMS.length; index++) {
    const { start_date, end_date } = terms[index] ?? {}

    if (start_date && end_date && today >= start_date && today <= end_date) {
      return TERMS[index]
    }
  }

  for (let index = 0; index < TERMS.length; index++) {
    const { start_date } = terms[index] ?? {}

    if (start_date && today < start_date) {
      return TERMS[index]
    }
  }

  return TERMS[TERMS.length - 1]
}

export function mapApiToFormData(data?: AcademicYearAndTerm): AcademicYearAndTermFormData {
  const termsByApiKey = Object.fromEntries((data?.terms ?? []).map((term) => [term.term, term]))

  const terms = TERMS.map((name) => ({
    name,
    start_date: termsByApiKey[TERM_NAME_TO_API[name]]?.start_date ?? '',
    end_date: termsByApiKey[TERM_NAME_TO_API[name]]?.end_date ?? '',
  }))

  return {
    academic_year: data?.academic_year ?? getCurrentAcademicYear(),
    current_term: data?.current_term
      ? TERM_API_TO_NAME[data.current_term]
      : guessCurrentTerm(terms),
    terms,
  }
}

export function mapFormToApiPayload(data: AcademicYearAndTermFormData): AcademicYearAndTermPayload {
  return {
    academic_year: data.academic_year,
    current_term: TERM_NAME_TO_API[data.current_term],
    terms: data.terms.map((term) => ({
      term: TERM_NAME_TO_API[term.name],
      start_date: term.start_date,
      end_date: term.end_date,
    })),
  }
}

export function getDefaultFormData(): AcademicYearAndTermFormData {
  const terms = defaultTerms()

  return {
    academic_year: getCurrentAcademicYear(),
    current_term: guessCurrentTerm(terms),
    terms,
  }
}
