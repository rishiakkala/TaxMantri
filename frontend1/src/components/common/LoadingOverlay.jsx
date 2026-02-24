import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const STEPS = [
  { label: 'Parsing your profile…', duration: 700 },
  { label: 'Calculating Old Regime tax…', duration: 800 },
  { label: 'Calculating New Regime tax…', duration: 800 },
  { label: 'Comparing regimes…', duration: 600 },
  { label: 'Generating optimisation tips…', duration: 600 },
]

/**
 * Full-screen animated loading overlay.
 *
 * Props:
 *   visible (bool)   — show/hide
 *   onComplete (fn)  — called after all steps finish (≥4s total)
 */
export default function LoadingOverlay({ visible, onComplete }) {
  const [stepIndex, setStepIndex] = useState(0)

  useEffect(() => {
    if (!visible) {
      setStepIndex(0)
      return
    }

    let idx = 0
    const advance = () => {
      if (idx >= STEPS.length - 1) {
        // All steps done — wait a beat then call onComplete
        setTimeout(() => onComplete?.(), 400)
        return
      }
      idx += 1
      setStepIndex(idx)
      setTimeout(advance, STEPS[idx].duration)
    }

    const timer = setTimeout(advance, STEPS[0].duration)
    return () => clearTimeout(timer)
  }, [visible, onComplete])

  const progress = ((stepIndex + 1) / STEPS.length) * 100

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-navy/95 backdrop-blur-sm"
        >
          {/* Spinning ring */}
          <div className="relative mb-8">
            <div className="w-20 h-20 rounded-full border-4 border-white/10" />
            <motion.div
              className="absolute inset-0 w-20 h-20 rounded-full border-4 border-t-amber border-r-amber border-b-transparent border-l-transparent animate-spin"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-amber font-bold text-lg">₹</span>
            </div>
          </div>

          <h2 className="text-white font-bold text-2xl mb-2">Analysing your tax…</h2>

          {/* Step label */}
          <AnimatePresence mode="wait">
            <motion.p
              key={stepIndex}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              className="text-navy-200 text-sm mb-8"
            >
              {STEPS[stepIndex].label}
            </motion.p>
          </AnimatePresence>

          {/* Progress bar */}
          <div className="w-64 h-1.5 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-amber rounded-full"
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
            />
          </div>

          {/* Step dots */}
          <div className="flex gap-2 mt-4">
            {STEPS.map((_, i) => (
              <motion.div
                key={i}
                className="w-2 h-2 rounded-full"
                animate={{
                  backgroundColor: i <= stepIndex ? '#f59e0b' : 'rgba(255,255,255,0.2)',
                  scale: i === stepIndex ? 1.3 : 1,
                }}
                transition={{ duration: 0.3 }}
              />
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
