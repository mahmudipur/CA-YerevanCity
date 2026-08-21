import { ChevronRightIcon, CheckCircleIcon } from '@heroicons/react/24/solid'
import type { ReviewRow } from '../../api/types'

const METHOD_LABEL: Record<string, string> = {
  'equal/all': 'Equal · everyone',
  single: 'Single person',
  'equal/partial': 'Equal · partial',
  percentage: 'Percentage',
  fixed: 'Fixed amount',
  ratio: 'Ratio',
}

export function ReviewList({ rows, onEdit }: { rows: ReviewRow[]; onEdit: (index: number) => void }) {
  return (
    <ul className="space-y-2">
      {rows.map((row) => {
        const entries = row.assignment ? Object.entries(row.assignment.assignments).filter(([, v]) => v > 0) : []
        return (
          <li key={row.index}>
            <button
              type="button"
              onClick={() => onEdit(row.index)}
              className="flex w-full min-h-11 cursor-pointer items-center justify-between gap-3 rounded-xl border border-[var(--color-border)] bg-surface px-3.5 py-3 text-left transition-colors hover:bg-[var(--color-surface-muted)]"
            >
              {row.item.image ? (
                <img
                  src={row.item.image}
                  alt=""
                  aria-hidden="true"
                  loading="lazy"
                  className="h-10 w-10 shrink-0 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] object-contain p-0.5"
                  onError={(e) => {
                    ;(e.currentTarget as HTMLImageElement).style.display = 'none'
                  }}
                />
              ) : null}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="truncate font-medium">{row.item.name}</span>
                  {row.assignment && <CheckCircleIcon className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />}
                </div>
                <div className="truncate text-xs text-text-muted">
                  {entries.length > 0
                    ? entries.map(([n, a]) => `${n}: ${a.toLocaleString()}`).join(' · ')
                    : 'Not assigned yet'}
                  {row.assignment && ` (${METHOD_LABEL[row.assignment.split_method] ?? row.assignment.split_method})`}
                </div>
              </div>
              <ChevronRightIcon className="h-4 w-4 shrink-0 text-text-muted" aria-hidden="true" />
            </button>
          </li>
        )
      })}
    </ul>
  )
}
