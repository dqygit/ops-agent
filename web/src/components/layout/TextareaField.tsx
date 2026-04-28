import type { TextareaHTMLAttributes } from 'react'

type TextareaFieldProps = {
  label: string
} & TextareaHTMLAttributes<HTMLTextAreaElement>

export function TextareaField({ label, id, className = '', ...props }: TextareaFieldProps) {
  const mergedClassName = className ? `field-control ${className}` : 'field-control'

  return (
    <>
      <label className="sr-only" htmlFor={id}>
        {label}
      </label>
      <textarea id={id} className={mergedClassName} {...props} />
    </>
  )
}
