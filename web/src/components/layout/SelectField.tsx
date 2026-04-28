import type { SelectHTMLAttributes } from 'react'

type SelectOption = {
  label: string
  value: string
}

type SelectFieldProps = {
  label: string
  options: SelectOption[]
} & SelectHTMLAttributes<HTMLSelectElement>

export function SelectField({ label, id, options, className = '', ...props }: SelectFieldProps) {
  const mergedClassName = className ? `field-control ${className}` : 'field-control'

  return (
    <>
      <label className="sr-only" htmlFor={id}>
        {label}
      </label>
      <select id={id} className={mergedClassName} {...props}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </>
  )
}
