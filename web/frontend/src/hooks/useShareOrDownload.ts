import { useCallback, useState } from 'react'

/** Fetches a file (e.g. the receipt image) and either opens the native
 * share sheet (mobile — straight into Photos or Tricount's attachment
 * picker) or falls back to a normal browser download (desktop, or any
 * browser without file-sharing support). */
export function useShareOrDownload() {
  const [isPending, setIsPending] = useState(false)

  const shareOrDownload = useCallback(async (url: string, filename: string, mimeType: string) => {
    setIsPending(true)
    try {
      const res = await fetch(url, { credentials: 'include' })
      if (!res.ok) throw new Error(`Request failed (${res.status})`)
      const blob = await res.blob()
      const file = new File([blob], filename, { type: mimeType })

      if (navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file] })
        return
      }

      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(objectUrl)
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') return // user cancelled the share sheet
      window.open(url, '_blank') // last-resort fallback
    } finally {
      setIsPending(false)
    }
  }, [])

  return { shareOrDownload, isPending }
}
