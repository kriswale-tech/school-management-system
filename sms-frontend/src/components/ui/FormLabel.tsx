import { mergeClasses } from '@/utils'

interface FormLabelProps {
  label: string
  required?: boolean
  className?: string
  helperText?: string
}

const defaultClassName = 'text-slate-700'

const FormLabel = ({ label, required, className, helperText }: FormLabelProps) => {
  const classes = mergeClasses(defaultClassName, className)
  return (
    <p className={classes}>
      {label}
      {helperText && <span className="text-sm ml-1">({helperText})</span>}
      {required && <span className="text-red-500 ml-1">*</span>}
    </p>
  )
}

export default FormLabel
