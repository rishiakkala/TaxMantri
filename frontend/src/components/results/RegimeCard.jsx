import { motion } from 'framer-motion'
import { CheckCircle, ChevronDown } from 'lucide-react'

const INR = (v) => '₹' + Number(v ?? 0).toLocaleString('en-IN')

/**
 * Single regime summary card.
 *
 * Props:
 *   regime        ('old' | 'new')
 *   data          — regime breakdown object from TaxResult
 *   isRecommended (bool)
 *   isExpanded    (bool)
 *   onClick       (fn)
 */
export default function RegimeCard({ regime, data, isRecommended, isExpanded, onClick }) {
  if (!data) return null

  const label = regime === 'old' ? 'Old Regime' : 'New Regime'
  const subtitle = regime === 'old' ? 'With deductions (80C, HRA, etc.)' : 'Simplified slabs (115BAC)'

  return (
    <motion.div
      onClick={onClick}
      style={{ transformPerspective: 1000 }}
      animate={{ rotateY: isExpanded ? 5 : 0, scale: isExpanded ? 0.98 : 1 }}
      transition={{ duration: 0.3 }}
      className={[
        'rounded-2xl border-2 cursor-pointer transition-shadow',
        'hover:shadow-lg active:scale-[0.98]',
        isRecommended
          ? 'border-success bg-success-light shadow-success/20'
          : 'border-gray-200 bg-white',
        isExpanded ? 'shadow-md' : '',
      ].join(' ')}
    >
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-navy text-lg">{label}</h3>
              {isRecommended && (
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-success bg-white px-2 py-0.5 rounded-full border border-success/30">
                  <CheckCircle className="w-3 h-3" />
                  Recommended
                </span>
              )}
            </div>
            <p className="text-gray-500 text-xs mt-0.5">{subtitle}</p>
          </div>
          <ChevronDown
            className={[
              'w-4 h-4 text-gray-400 transition-transform mt-1',
              isExpanded ? 'rotate-180' : '',
            ].join(' ')}
          />
        </div>

        {/* Total tax — hero number */}
        <div className="mb-4">
          <p className="text-xs text-gray-500 mb-0.5">Total Tax Payable</p>
          <p className={[
            'text-3xl font-extrabold tracking-tight',
            isRecommended ? 'text-success' : 'text-navy',
          ].join(' ')}>
            {INR(data.total_tax)}
          </p>
          {data.cess > 0 && (
            <p className="text-xs text-gray-400 mt-0.5">
              incl. ₹{Number(data.cess).toLocaleString('en-IN')} cess
            </p>
          )}
        </div>

        {/* Key stats */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Gross Income</span>
            <span className="font-medium text-gray-800">{INR(data.gross_income)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Total Deductions</span>
            <span className="font-medium text-gray-800">{INR(data.total_deductions)}</span>
          </div>
          <div className="flex justify-between text-sm border-t border-gray-100 pt-2 mt-2">
            <span className="text-gray-700 font-medium">Taxable Income</span>
            <span className="font-semibold text-navy">{INR(data.taxable_income)}</span>
          </div>
        </div>

        <p className="text-xs text-center text-gray-400 mt-4">
          Click to see full breakdown
        </p>
      </div>
    </motion.div>
  )
}
