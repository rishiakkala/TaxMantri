import { motion } from 'framer-motion'
import { TrendingDown, Minus } from 'lucide-react'

const INR = (v) => '₹' + Math.abs(Number(v)).toLocaleString('en-IN')

/**
 * Props:
 *   taxResult — full TaxResult from backend
 */
export default function SavingsBanner({ taxResult }) {
  if (!taxResult) return null

  const { recommended_regime, savings_amount } = taxResult
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
        </div>
      </motion.div>
    )
  }

  const regimeLabel = recommended_regime === 'old' ? 'Old Regime' : 'New Regime'

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-3xl bg-custom-green/10 border border-custom-green/20 p-6 mb-6 flex items-start gap-4 shadow-sm"
    >
      <div className="w-12 h-12 rounded-2xl bg-custom-green flex items-center justify-center flex-shrink-0 flex-none shadow-md shadow-custom-green/20">
        <TrendingDown className="w-6 h-6 text-black" />
      </div>
      <div className="pt-1">
        <p className="font-extrabold text-black text-xl">
          You save <span className="text-custom-green">{INR(savings)}</span> with{' '}
          {regimeLabel}
        </p>
      </div>
    </motion.div>
  )
}
