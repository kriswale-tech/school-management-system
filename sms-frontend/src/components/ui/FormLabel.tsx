import { mergeClasses } from '@/utils'

interface FormLabelProps {
  label: string
  required?: boolean
  className?: string
}

const defaultClassName = 'text-lg font-medium text-slate-700'

const FormLabel = ({ label, required, className }: FormLabelProps) => {
  const classes = mergeClasses(defaultClassName, className)
  return (
    <p className={classes}>
      {label}
      {required && <span className="text-red-500 ml-1">*</span>}
    </p>
  )
}

export default FormLabel
