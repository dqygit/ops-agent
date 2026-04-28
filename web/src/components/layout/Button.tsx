import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ButtonVariant = 'default' | 'primary' | 'danger' | 'tab-active'

type ButtonProps = {
  children: ReactNode
  variant?: ButtonVariant
} & ButtonHTMLAttributes<HTMLButtonElement>

export function Button({ children, className = '', variant = 'default', type = 'button', ...props }: ButtonProps) {
  const variantClassName = {
    default: 'button button-default',
    primary: 'button button-primary',
    danger: 'button button-danger',
    'tab-active': 'button button-tab-active',
  }[variant]

  const mergedClassName = className ? `${variantClassName} ${className}` : variantClassName

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
