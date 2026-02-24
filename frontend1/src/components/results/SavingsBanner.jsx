import { motion } from 'framer-motion'
import { TrendingDown, Minus } from 'lucide-react'

const INR = (v) => '₹' + Math.abs(Number(v)).toLocaleString('en-IN')

/**
 * Props:
 *   taxResult — full TaxResult from backend
 */
export default function SavingsBanner({ taxResult }) {
  if (!taxResult) return null

  const { recommended_regime, savings_amount, rationale } = taxResult
  const savings = Number(savings_amount ?? 0)

  if (savings === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl bg-gray-100 border border-gray-200 p-5 mb-6 flex items-center gap-4"
      >
        <div className="w-10 h-10 rounded-xl bg-gray-300 flex items-center justify-center flex-shrink-0">
          <Minus className="w-5 h-5 text-gray-600" />
        </div>
        <div>
          <p className="font-semibold text-gray-800">Both regimes result in the same tax.</p>
          {rationale && <p className="text-gray-600 text-sm mt-0.5">{rationale}</p>}
        </div>
      </motion.div>
    )
  }

  const regimeLabel = recommended_regime === 'old' ? 'Old Regime' : 'New Regime'

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl bg-success-light border border-success/30 p-5 mb-6 flex items-start gap-4"
    >
      <div className="w-10 h-10 rounded-xl bg-success flex items-center justify-center flex-shrink-0 flex-none">
        <TrendingDown className="w-5 h-5 text-white" />
      </div>
      <div>
        <p className="font-bold text-success text-lg">
          You save <span className="underline decoration-dotted">{INR(savings)}</span> with{' '}
          {regimeLabel}
        </p>
        {rationale && (
          <p className="text-green-800 text-sm mt-1 leading-relaxed">{rationale}</p>
        )}
      </div>
    </motion.div>
  )
}
