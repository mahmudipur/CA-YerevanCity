import { useId } from 'react'
import { motion } from 'framer-motion'

interface Props {
  value: string
  unit: '%' | 'AMD'
  onValueChange: (v: string) => void
  onUnitChange: (u: '%' | 'AMD') => void
  placeholder?: string
}

/** Numeric input paired with a tappable %/AMD toggle, so the unit is chosen
 * with one tap instead of typing a symbol that needs a second keyboard on
 * mobile. */
export function UnitToggleInput({ value, unit, onValueChange, onUnitChange, placeholder }: Props) {
  const layoutId = useId()
  return (
    <div className="flex min-h-11 items-stretch overflow-hidden rounded-xl border border-[var(--color-border)]">
      <input
        type="number"
        inputMode="decimal"
        value={value}
        onChange={(e) => onValueChange(e.target.value)}
        placeholder={placeholder}
        className="min-w-0 flex-1 bg-transparent px-3.5 py-2.5 font-mono-num outline-none"
      />
      <div className="relative m-1 flex shrink-0 rounded-lg bg-[var(--color-surface-muted)] p-0.5">
        {(['%', 'AMD'] as const).map((u) => (
          <button
            key={u}
            type="button"
            onClick={() => onUnitChange(u)}
            aria-pressed={unit === u}
            className="relative min-w-[38px] cursor-pointer rounded-md px-2 py-1 text-xs font-semibold"
          >
            {unit === u && (
              <motion.span
                layoutId={`unit-toggle-active-${layoutId}`}
                className="absolute inset-0 rounded-md bg-primary"
                transition={{ type: 'spring', stiffness: 400, damping: 32 }}
              />
            )}
            <span className={`relative ${unit === u ? 'text-on-primary' : 'text-text-muted'}`}>{u}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
