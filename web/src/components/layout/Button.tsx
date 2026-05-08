import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ButtonVariant = 'default' | 'primary' | 'danger' | 'tab-active'

type ButtonProps = {
  children: ReactNode
  variant?: ButtonVariant
} & ButtonHTMLAttributes<HTMLButtonElement>

export function Button({ children, className = '', variant = 'default', type = 'button', ...props }: ButtonProps) {
  const baseClasses = 'inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium transition-colors focus:outline-none'
  const variantClassName = {
    default: 'border-ops-border/70 bg-ops-panel text-ops-text hover:border-ops-border hover:bg-ops-deep',
    primary: 'border-ops-green/60 bg-[rgb(132_204_22_/_0.12)] text-ops-green hover:border-ops-green hover:bg-[rgb(132_204_22_/_0.18)]',
    danger: 'border-ops-danger/60 bg-[rgb(239_68_68_/_0.12)] text-ops-danger hover:border-ops-danger hover:bg-[rgb(239_68_68_/_0.18)]',
    'tab-active': 'rounded-none border-b-ops-green border-l-ops-border/70 border-r-ops-border/70 border-t-transparent bg-ops-deep text-ops-green',
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
