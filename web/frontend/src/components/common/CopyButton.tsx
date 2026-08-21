import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ClipboardDocumentIcon, CheckIcon } from '@heroicons/react/24/outline'
import { Button } from './Button'

export function CopyButton({ text, label = 'Copy prompt' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      // Fallback for browsers/contexts without Clipboard API permission.
      const el = document.createElement('textarea')
      el.value = text
      el.style.position = 'fixed'
      el.style.opacity = '0'
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }

  return (
    <Button
      type="button"
      variant={copied ? 'secondary' : 'primary'}
      fullWidth
      onClick={handleCopy}
      icon={
        <AnimatePresence mode="wait" initial={false}>
          {copied ? (
            <motion.span
              key="check"
              initial={{ scale: 0.5, rotate: -30, opacity: 0 }}
              animate={{ scale: 1, rotate: 0, opacity: 1 }}
              exit={{ scale: 0.5, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 500, damping: 20 }}
            >
              <CheckIcon className="h-4 w-4 text-primary" />
            </motion.span>
          ) : (
            <motion.span key="clip" initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.5, opacity: 0 }}>
              <ClipboardDocumentIcon className="h-4 w-4" />
            </motion.span>
          )}
        </AnimatePresence>
      }
    >
      {copied ? 'Copied!' : label}
    </Button>
  )
}
