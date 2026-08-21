export interface CountryCode {
  code: string // dialing code, e.g. "+374"
  iso: string // ISO 3166-1 alpha-2
  name: string
  flag: string
}

// Armenia first (this app's home market), then a practical set of
// commonly-needed codes. Not exhaustive — good enough for a personal tool.
export const COUNTRY_CODES: CountryCode[] = [
  { code: '+374', iso: 'AM', name: 'Armenia', flag: '🇦🇲' },
  { code: '+7', iso: 'RU', name: 'Russia', flag: '🇷🇺' },
  { code: '+995', iso: 'GE', name: 'Georgia', flag: '🇬🇪' },
  { code: '+90', iso: 'TR', name: 'Turkey', flag: '🇹🇷' },
  { code: '+971', iso: 'AE', name: 'UAE', flag: '🇦🇪' },
  { code: '+1', iso: 'US', name: 'United States', flag: '🇺🇸' },
  { code: '+44', iso: 'GB', name: 'United Kingdom', flag: '🇬🇧' },
  { code: '+33', iso: 'FR', name: 'France', flag: '🇫🇷' },
  { code: '+49', iso: 'DE', name: 'Germany', flag: '🇩🇪' },
]

export const DEFAULT_COUNTRY = COUNTRY_CODES[0]
