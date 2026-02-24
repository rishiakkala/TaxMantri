import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertCircle, X } from 'lucide-react'

/**
 * Dismissible error banner.
 *
 * Props:
 *   error  — string message OR backend error object { code, message, details[] }
 *   onDismiss (fn, optional) — called when user dismisses
 */
export default function ErrorBanner({ error, onDismiss }) {
  const [dismissed, setDismissed] = useState(false)

  if (!error || dismissed) return null

  const message = typeof error === 'string'
    ? error
    : error?.error?.message ?? error?.message ?? 'An unexpected error occurred.'

  const details = typeof error === 'object'
    ? (error?.error?.details ?? error?.details ?? [])
    : []

  const handleDismiss = () => {
    setDismissed(true)
    onDismiss?.()
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        className="rounded-xl border border-red-200 bg-red-50 p-4 mb-4"
      >
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-red-800 font-medium text-sm">{message}</p>
            {details.length > 0 && (
              <ul className="mt-2 space-y-1">
                {details.map((d, i) => (
                  <li key={i} className="text-red-700 text-xs">
                    {d.field && <span className="font-mono font-semibold">{d.field}: </span>}
                    {d.issue}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button
            onClick={handleDismiss}
            className="flex-shrink-0 text-red-400 hover:text-red-600 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  )
}
