import CurrencyInput from '../../common/CurrencyInput.jsx'

/**
 * Step 3 — Housing (HRA / rent).
 */
export default function Step3Housing({ register, errors }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-navy mb-1">Housing Details</h2>
        <p className="text-gray-500 text-sm">
          Used for HRA exemption under Rule 2A. Leave rent at ₹0 if you don't pay rent.
        </p>
      </div>

      <CurrencyInput
        label="Monthly Rent Paid (₹)"
        error={errors.monthly_rent_paid?.message}
        helpText="Enter the amount you pay each month. ₹0 if not paying rent."
        {...register('monthly_rent_paid', { valueAsNumber: true })}
      />

      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">
          City Type <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-2 gap-3">
          {[
            { value: 'metro', label: 'Metro', desc: 'Mumbai, Delhi, Chennai, Kolkata (50% of basic)' },
            { value: 'non_metro', label: 'Non-Metro', desc: 'All other cities (40% of basic)' },
          ].map((opt) => (
            <label
              key={opt.value}
              className="relative cursor-pointer"
            >
              <input
                type="radio"
                value={opt.value}
                className="sr-only peer"
                {...register('city_type')}
              />
              <div className="border-2 rounded-xl p-4 transition-all peer-checked:border-navy peer-checked:bg-navy/5 border-gray-200 hover:border-gray-300">
                <div className="font-semibold text-sm text-gray-800">{opt.label}</div>
                <div className="text-xs text-gray-500 mt-0.5">{opt.desc}</div>
              </div>
            </label>
          ))}
        </div>
        {errors.city_type && (
          <p className="text-red-600 text-xs">{errors.city_type.message}</p>
        )}
      </div>
    </div>
  )
}
