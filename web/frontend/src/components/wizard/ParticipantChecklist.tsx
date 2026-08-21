import { motion } from 'framer-motion'
import { CheckIcon } from '@heroicons/react/24/solid'
import clsx from 'clsx'

interface Props {
  participants: string[]
  selected: string[]
  onChange: (next: string[]) => void
}

export function ParticipantChecklist({ participants, selected, onChange }: Props) {
  function toggle(name: string) {
    if (selected.includes(name)) {
      onChange(selected.filter((n) => n !== name))
    } else {
      onChange([...selected, name])
    }
  }

  return (
    <fieldset>
      <legend className="mb-2 text-sm font-medium text-text-muted">Who shares this item?</legend>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {participants.map((name) => {
          const checked = selected.includes(name)
          return (
            <button
              key={name}
              type="button"
              role="checkbox"
              aria-checked={checked}
              onClick={() => toggle(name)}
              className={clsx(
                'flex min-h-11 items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-sm font-medium',
                'cursor-pointer transition-colors duration-150',
                checked
                  ? 'border-primary bg-primary/10 text-text'
                  : 'border-[var(--color-border)] bg-surface text-text-muted hover:bg-[var(--color-surface-muted)]',
              )}
            >
              <motion.span
                initial={false}
                animate={checked ? { scale: 1, backgroundColor: 'var(--color-primary)' } : { scale: 1 }}
                className={clsx(
                  'flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2',
                  checked ? 'border-primary' : 'border-[var(--color-border)]',
                )}
              >
                {checked && <CheckIcon className="h-3.5 w-3.5 text-on-primary" />}
              </motion.span>
              <span className="truncate">{name}</span>
            </button>
          )
        })}
      </div>
    </fieldset>
  )
}
