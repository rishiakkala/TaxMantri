import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FileSearch, Calculator, Database, LineChart } from 'lucide-react'

const STEPS = [
  { label: 'Data reading', icon: FileSearch, duration: 1500 },
  { label: 'TAX Calculation', icon: Calculator, duration: 1500 },
  { label: 'Regime Calculation', icon: Database, duration: 2500 },
  { label: 'Results Generation', icon: LineChart, duration: 1500 },
]

/**
 * Full-screen animated loading overlay matching the user's sketch.
 *
 * Props:
 *   visible (bool)   — show/hide
 *   onComplete (fn)  — called after all steps finish
 */
export default function LoadingOverlay({ visible, onComplete }) {
  const [stepIndex, setStepIndex] = useState(0)

  useEffect(() => {
    if (!visible) {
      setStepIndex(0)
      return
    }

    let idx = 0
    let timer = null
    const advance = () => {
      if (idx >= STEPS.length - 1) {
        // All steps done — wait a beat then call onComplete
        timer = setTimeout(() => onComplete?.(), 600)
        return
      }
      idx += 1
      setStepIndex(idx)
      timer = setTimeout(advance, STEPS[idx].duration)
    }

    timer = setTimeout(advance, STEPS[0].duration)
    return () => clearTimeout(timer)
  }, [visible, onComplete])

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          // Added z-[100] to ensure it covers the Navbar!
          className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-black/95 backdrop-blur-xl"
        >
          {/* Title */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-14 text-center"
          >
            <h2 className="text-white font-extrabold text-3xl md:text-4xl mb-3 tracking-tight">
              Agents working in the background
            </h2>
            <div className="w-32 h-1 bg-gradient-to-r from-transparent via-white/40 to-transparent mx-auto rounded-full" />
          </motion.div>

          {/* 4 Boxes Grid */}
          <div className="flex flex-wrap items-center justify-center gap-6 md:gap-8 max-w-6xl px-6">
            {STEPS.map((step, i) => {
              const isActive = i === stepIndex;
              const isPast = i < stepIndex;
              const isPending = i > stepIndex;

              const Icon = step.icon;

              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className={`
                    relative flex flex-col items-center justify-center w-40 h-40 md:w-52 md:h-52 rounded-3xl border transition-all duration-700
                    ${isPast ? 'bg-white/10 border-white/20 text-white' : ''}
                    ${isActive ? 'bg-white text-black border-white shadow-[0_0_50px_rgba(255,255,255,0.4)] scale-110 z-10' : ''}
                    ${isPending ? 'bg-white/5 border-white/5 text-gray-500' : ''}
                  `}
                >
                  <motion.div
                    animate={isActive ? { scale: [1, 1.15, 1], rotate: [0, 5, -5, 0] } : {}}
                    transition={{ repeat: isActive ? Infinity : 0, duration: 2, ease: "easeInOut" }}
                    className="mb-4"
                  >
                    <Icon className="w-10 h-10 md:w-12 md:h-12" />
                  </motion.div>

                  <p className="font-extrabold text-center text-sm md:text-lg leading-tight px-4">{step.label}</p>

                  {/* Status Indicator */}
                  <div className="absolute bottom-4 flex items-center gap-2">
                    {isPast && <span className="text-[10px] md:text-xs font-bold uppercase tracking-widest text-green-500">Done</span>}
                    {isActive && <span className="text-[10px] md:text-xs font-bold uppercase tracking-widest animate-pulse text-gray-500">Processing...</span>}
                    {isPending && <span className="text-[10px] md:text-xs font-bold uppercase tracking-widest text-gray-600">Waiting</span>}
                  </div>
                </motion.div>
              )
            })}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
