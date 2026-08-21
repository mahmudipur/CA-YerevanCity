import type { HTMLAttributes } from 'react'
import clsx from 'clsx'

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        'rounded-2xl border border-[var(--color-border)] bg-surface p-4 shadow-[var(--shadow-card)] sm:p-5',
        className,
      )}
      {...props}
    />
  )
}
