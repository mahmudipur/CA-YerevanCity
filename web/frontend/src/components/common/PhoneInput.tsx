import { ChevronDownIcon } from '@heroicons/react/24/outline'
import { COUNTRY_CODES } from '../../data/countryCodes'

interface Props {
  countryCode: string
  national: string
  onCountryChange: (code: string) => void
  onNationalChange: (digits: string) => void
  disabled?: boolean
}

/** Single phone field: country-code dropdown + national number. The full
 * E.164 number is derived by the caller (countryCode + national) — the
 * user never has to type or reconcile two separate phone strings. */
export function PhoneInput({ countryCode, national, onCountryChange, onNationalChange, disabled }: Props) {
  return (
    <div className="flex items-stretch gap-2">
      <div className="relative shrink-0">
        <select
          value={countryCode}
          disabled={disabled}
          onChange={(e) => onCountryChange(e.target.value)}
          className="min-h-11 w-[92px] appearance-none rounded-xl border border-[var(--color-border)] bg-transparent pl-3 pr-6 py-2.5 outline-none disabled:opacity-50"
          aria-label="Country code"
        >
          {COUNTRY_CODES.map((c) => (
            <option key={c.iso} value={c.code}>
              {c.flag} {c.code}
            </option>
          ))}
        </select>
        <ChevronDownIcon className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-muted" />
      </div>
      <input
        type="tel"
        inputMode="numeric"
        autoComplete="tel-national"
        disabled={disabled}
        placeholder="55285320"
        value={national}
        onChange={(e) => onNationalChange(e.target.value.replace(/\D/g, ''))}
        className="min-h-11 w-full rounded-xl border border-[var(--color-border)] bg-transparent px-3.5 py-2.5 outline-none disabled:opacity-50"
      />
    </div>
  )
}
