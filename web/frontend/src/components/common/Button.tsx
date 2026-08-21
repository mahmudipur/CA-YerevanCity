import { motion } from 'framer-motion'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import clsx from 'clsx'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  loading?: boolean
  icon?: ReactNode
  fullWidth?: boolean
}

const variantClasses: Record<Variant, string> = {
  primary: 'bg-primary text-on-primary hover:bg-[var(--color-primary-hover)] shadow-[var(--shadow-card)]',
  secondary:
    'bg-surface text-text border border-[var(--color-border)] hover:bg-[var(--color-surface-muted)]',
  ghost: 'bg-transparent text-text hover:bg-[var(--color-surface-muted)]',
  danger: 'bg-accent text-on-accent hover:opacity-90',
}

export function Button({
  variant = 'primary',
  loading,
  icon,
  fullWidth,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <motion.button
      whileTap={{ scale: disabled || loading ? 1 : 0.97 }}
      className={clsx(
        'inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-5 py-2.5',
        'text-[15px] font-semibold transition-colors duration-150 cursor-pointer select-none',
        'disabled:cursor-not-allowed disabled:opacity-50',
        fullWidth && 'w-full',
        variantClasses[variant],
        className,
      )}
      disabled={disabled || loading}
      {...(props as React.ComponentProps<typeof motion.button>)}
    >
      {loading ? (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        icon
      )}
      {children}
    </motion.button>
  )
}
