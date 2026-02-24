import { motion } from 'framer-motion'
import { X, Lightbulb } from 'lucide-react'

const INR = (v) => '₹' + Number(v ?? 0).toLocaleString('en-IN')

const DEDUCTION_LABELS = {
  standard_deduction: 'Standard Deduction',
  hra_exemption: 'HRA Exemption',
  section_80c: '80C Investments',
  section_80d: '80D Health Insurance (self + parents)',
  section_80ccd1b: 'NPS 80CCD(1B)',
  section_80ccd2: 'Employer NPS 80CCD(2)',
  section_24b: 'Home Loan Interest 24(b)',
  section_80tta_ttb: 'Savings Interest 80TTA/TTB',
  professional_tax: 'Professional Tax',
}

/**
 * Props:
 *   regime    ('old' | 'new')
 *   data      — regime breakdown from TaxResult
 *   taxResult — full TaxResult (for suggestions)
 *   side      ('left' | 'right') — animation direction
 *   onClose   (fn)
 */
export default function DetailPanel({ regime, data, taxResult, side, onClose }) {
  if (!data) return null

  const label = regime === 'old' ? 'Old Regime' : 'New Regime'
  const suggestions = regime === 'old'
    ? (taxResult?.old_regime_suggestions ?? taxResult?.optimization_suggestions ?? [])
    : (taxResult?.new_regime_suggestions ?? [])

  const breakdown = data.deduction_breakdown ?? {}
  const filledDeductions = Object.entries(breakdown).filter(([, v]) => Number(v) > 0)

  return (
    <motion.div
      initial={{ opacity: 0, x: side === 'left' ? -80 : 80 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: side === 'left' ? -80 : 80 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="rounded-3xl border border-gray-100 bg-white shadow-[0_20px_40px_rgb(0,0,0,0.12)] overflow-hidden flex flex-col h-full"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-5 bg-custom-dark text-white">
        <div>
          <h3 className="font-extrabold text-xl">{label} — Full Breakdown</h3>
          <p className="text-gray-400 text-sm font-medium mt-1">
            Total Tax: {INR(data.total_tax)}
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-2 rounded-xl hover:bg-white/10 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin p-5 space-y-5">
        {/* Income summary */}
        <section>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Income Summary
          </h4>
          <div className="space-y-1.5">
            {[
              { label: 'Gross Income', value: data.gross_income },
              { label: 'Total Deductions', value: data.total_deductions, negative: true },
              { label: 'Taxable Income', value: data.taxable_income, bold: true },
              { label: 'Tax Before Cess', value: data.tax_before_cess },
              { label: '4% Health & Education Cess', value: data.cess },
              { label: 'Total Tax Payable', value: data.total_tax, bold: true, highlight: true },
            ].map((row, i) => (
              <div
                key={i}
                className={[
                  'flex justify-between items-center py-2 px-3 rounded-xl text-[15px]',
                  row.highlight ? 'bg-custom-purple/10 border border-custom-purple/20' : '',
                ].join(' ')}
              >
                <span className={row.bold ? 'font-bold text-gray-900' : 'text-gray-600'}>
                  {row.label}
                </span>
                <span className={[
                  row.bold ? 'font-extrabold' : 'font-semibold',
                  row.highlight ? 'text-custom-purple' : 'text-gray-800',
                  row.negative ? 'text-custom-green' : '',
                ].join(' ')}>
                  {row.negative ? `−${INR(row.value)}` : INR(row.value)}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Deduction breakdown */}
        {filledDeductions.length > 0 && (
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Deduction Breakdown
            </h4>
            <div className="rounded-xl border border-gray-200 overflow-hidden">
              {filledDeductions.map(([key, value], i) => (
                <div
                  key={key}
                  className={[
                    'flex justify-between items-center px-4 py-2.5 text-sm',
                    i > 0 ? 'border-t border-gray-100' : '',
                  ].join(' ')}
                >
                  <span className="text-gray-600">
                    {DEDUCTION_LABELS[key] ?? key}
                  </span>
                  <span className="font-bold text-custom-green">
                    −{INR(value)}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Optimisation suggestions */}
        {suggestions.length > 0 && (
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
              <Lightbulb className="w-3.5 h-3.5 text-amber" />
              Optimisation Tips
            </h4>
            <div className="space-y-2">
              {suggestions.map((tip, i) => (
                <div
                  key={i}
                  className="flex gap-2.5 bg-amber/5 border border-amber/20 rounded-xl p-3"
                >
                  <span className="text-amber font-bold text-sm flex-shrink-0">{i + 1}.</span>
                  <p className="text-gray-700 text-sm leading-relaxed">{tip}</p>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </motion.div>
  )
}
