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
      animate={{ scale: isExpanded ? 0.98 : 1 }}
      transition={{ duration: 0.3 }}
      className={[
        'rounded-3xl border cursor-pointer transition-all duration-300 relative overflow-hidden',
        'hover:shadow-[0_20px_40px_rgb(0,0,0,0.08)] active:scale-[0.98] group',
        isRecommended
          ? 'border-custom-green bg-custom-green/5 shadow-[0_8px_30px_rgb(46,172,133,0.15)] ring-2 ring-custom-green/20'
          : 'border-gray-100 bg-white shadow-[0_8px_30px_rgb(0,0,0,0.04)]',
        isExpanded ? 'ring-2 ring-custom-purple border-custom-purple bg-gray-50' : '',
      ].join(' ')}
    >
      {/* Recommended Badge Gradient */}
      {isRecommended && (
        <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-custom-green to-[#5ce1ca]" />
      )}
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3">
              <h3 className="font-extrabold text-black text-xl">{label}</h3>
              {isRecommended && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-custom-green bg-white px-3 py-1 rounded-full border border-custom-green/30 shadow-sm">
                  <CheckCircle className="w-3.5 h-3.5" />
                  Recommended
                </span>
              )}
            </div>
            <p className="text-gray-500 text-sm mt-1 font-medium">{subtitle}</p>
          </div>
          <ChevronDown
            className={[
              'w-4 h-4 text-gray-400 transition-transform mt-1',
              isExpanded ? 'rotate-180' : '',
            ].join(' ')}
          />
        </div>

        {/* Total tax — hero number */}
        <div className="mb-6">
          <p className="text-sm font-medium text-gray-500 mb-1">Total Tax Payable</p>
          <p className={[
            'text-4xl font-extrabold tracking-tight',
            isRecommended ? 'text-custom-green' : 'text-black',
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
        <div className="space-y-3">
          <div className="flex justify-between text-[15px]">
            <span className="text-gray-500 font-medium">Gross Income</span>
            <span className="font-bold text-gray-900">{INR(data.gross_income)}</span>
          </div>
          <div className="flex justify-between text-[15px]">
            <span className="text-gray-500 font-medium">Total Deductions</span>
            <span className="font-bold text-gray-900">{INR(data.total_deductions)}</span>
          </div>
          <div className="flex justify-between text-[15px] border-t border-gray-100 pt-3 mt-3">
            <span className="text-gray-800 font-bold">Taxable Income</span>
            <span className="font-extrabold text-black">{INR(data.taxable_income)}</span>
          </div>
        </div>

        <p className="text-sm text-center text-custom-purple font-semibold mt-6 opacity-0 group-hover:opacity-100 transition-opacity">
          Click to see full breakdown
        </p>
      </div>
    </motion.div>
  )
}
