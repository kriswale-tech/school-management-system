import React from 'react'

type FormWrapperProps = {
  children: React.ReactNode
  widthPx?: number
}

const FormWrapper = ({ children, widthPx = 690 }: FormWrapperProps) => {
  return (
    <div className="bg-white p-12 rounded-3xl" style={{ width: `${widthPx}px` }}>
      {children}
    </div>
  )
}

export default FormWrapper
