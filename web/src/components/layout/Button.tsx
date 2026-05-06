import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ButtonVariant = 'default' | 'primary' | 'danger' | 'tab-active'

type ButtonProps = {
  children: ReactNode
  variant?: ButtonVariant
} & ButtonHTMLAttributes<HTMLButtonElement>

export function Button({ children, className = '', variant = 'default', type = 'button', ...props }: ButtonProps) {
  const baseClasses = "inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md transition-colors focus:outline-none"
  const variantClassName = {
    default: 'text-ops-text bg-ops-border/10 hover:bg-ops-border/20 border border-transparent',
    primary: 'text-ops-bg bg-ops-cyan hover:bg-ops-cyan/90 border border-transparent',
    danger: 'text-white bg-red-600 hover:bg-red-700 border border-transparent',
    'tab-active': 'bg-ops-border/20 text-ops-cyan border-b-2 border-ops-cyan rounded-b-none',
  }[variant]

  const mergedClassName = `${baseClasses} ${variantClassName} ${className}`.trim()

  return (
    <button type={type} className={mergedClassName} {...props}>
      {children}
    </button>
  )
}

export function PrimaryButton(props: Omit<ButtonProps, 'variant'>) {
  return <Button variant="primary" {...props} />
}

export function DangerButton(props: Omit<ButtonProps, 'variant'>) {
  return <Button variant="danger" {...props} />
}

export function SecondaryButton(props: Omit<ButtonProps, 'variant'>) {
  return <Button variant="default" {...props} />
}
