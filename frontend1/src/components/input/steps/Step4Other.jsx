import CurrencyInput from '../../common/CurrencyInput.jsx'

const AGE_OPTIONS = [
  { value: 'under60', label: 'Under 60', desc: 'Standard tax slabs & limits' },
  { value: '60_79', label: '60–79', desc: 'Senior citizen — higher 80D limits' },
  { value: '80plus', label: '80+', desc: 'Super senior — no tax up to ₹5L (old)' },
]

/**
 * Step 4 — Other details (age bracket, other income).
 */
export default function Step4Other({ register, errors }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-navy mb-1">Other Details</h2>
        <p className="text-gray-500 text-sm">
          Age bracket affects tax slabs and deduction limits.
        </p>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">
          Age Bracket <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-3 gap-3">
          {AGE_OPTIONS.map((opt) => (
            <label key={opt.value} className="relative cursor-pointer">
              <input
                type="radio"
                value={opt.value}
                className="sr-only peer"
                {...register('age_bracket')}
              />
              <div className="border-2 rounded-xl p-3 text-center transition-all peer-checked:border-navy peer-checked:bg-navy/5 border-gray-200 hover:border-gray-300">
                <div className="font-semibold text-sm text-gray-800">{opt.label}</div>
                <div className="text-xs text-gray-500 mt-0.5 leading-tight">{opt.desc}</div>
              </div>
            </label>
          ))}
        </div>
        {errors.age_bracket && (
          <p className="text-red-600 text-xs">{errors.age_bracket.message}</p>
        )}
      </div>

      <CurrencyInput
        label="Other Income (Annual)"
        error={errors.other_income?.message}
        helpText="Interest income, FD, freelance earnings, etc."
        {...register('other_income', { valueAsNumber: true })}
      />
    </div>
  )
}
