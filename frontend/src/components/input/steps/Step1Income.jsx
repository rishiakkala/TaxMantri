import CurrencyInput from '../../common/CurrencyInput.jsx'

/**
 * Step 1 — Income fields.
 * Uses react-hook-form register/errors passed down from ManualWizard.
 */
export default function Step1Income({ register, errors }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-navy mb-1">Income Details</h2>
        <p className="text-gray-500 text-sm">Enter your annual salary components from your salary slip or Form 16.</p>
      </div>

      <CurrencyInput
        label="Basic Salary (Annual)"
        required
        error={errors.basic_salary?.message}
        helpText="Annual basic salary before deductions · ITR-1 limit: ₹50,00,000"
        {...register('basic_salary', { valueAsNumber: true })}
      />

      <CurrencyInput
        label="HRA Received (Annual)"
        error={errors.hra_received?.message}
        helpText="House Rent Allowance component from CTC"
        {...register('hra_received', { valueAsNumber: true })}
      />

      <CurrencyInput
        label="Leave Travel Allowance (Annual)"
        error={errors.lta?.message}
        {...register('lta', { valueAsNumber: true })}
      />

      <CurrencyInput
        label="Special Allowance (Annual)"
        error={errors.special_allowance?.message}
        helpText="Performance / special allowance from employer"
        {...register('special_allowance', { valueAsNumber: true })}
      />

      <CurrencyInput
        label="Other Allowances (Annual)"
        error={errors.other_allowances?.message}
        helpText="Any other allowances not listed above"
        {...register('other_allowances', { valueAsNumber: true })}
      />

      <CurrencyInput
        label="Professional Tax (Annual)"
        error={errors.professional_tax?.message}
        helpText="Deducted by employer; max ₹2,400/year"
        {...register('professional_tax', { valueAsNumber: true })}
      />
    </div>
  )
}
