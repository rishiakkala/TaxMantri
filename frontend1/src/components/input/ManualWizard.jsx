import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import WizardProgressBar from './WizardProgressBar.jsx'
import Step1Income from './steps/Step1Income.jsx'
import Step2Deductions from './steps/Step2Deductions.jsx'
import Step3Housing from './steps/Step3Housing.jsx'
import Step4Other from './steps/Step4Other.jsx'
import Step5Review from './steps/Step5Review.jsx'
import ErrorBanner from '../common/ErrorBanner.jsx'
import { createProfile, calculateTax } from '../../api/endpoints.js'

// ---- Zod schema ----
const schema = z.object({
  // Step 1 — Income
  basic_salary: z.number({ invalid_type_error: 'Required' }).min(0, 'Must be ≥ 0'),
  hra_received: z.number().min(0).default(0).optional(),
  lta: z.number().min(0).default(0).optional(),
  special_allowance: z.number().min(0).default(0).optional(),
  other_allowances: z.number().min(0).default(0).optional(),
  professional_tax: z.number().min(0).max(2400, 'Max ₹2,400').default(0).optional(),

  // Step 2 — Deductions
  investments_80c: z.number().min(0).max(150000, 'Max ₹1,50,000').default(0).optional(),
  health_insurance_self: z.number().min(0).default(0).optional(),
  health_insurance_parents: z.number().min(0).default(0).optional(),
  parent_senior_citizen: z.boolean().default(false).optional(),
  employee_nps_80ccd1b: z.number().min(0).max(50000, 'Max ₹50,000').default(0).optional(),
  employer_nps_80ccd2: z.number().min(0).default(0).optional(),
  home_loan_interest: z.number().min(0).max(200000, 'Max ₹2,00,000').default(0).optional(),
  savings_interest_80tta: z.number().min(0).default(0).optional(),

  // Step 3 — Housing
  monthly_rent_paid: z.number().min(0).default(0).optional(),
  city_type: z.enum(['metro', 'non_metro'], { required_error: 'Select city type' }),

  // Step 4 — Other
  age_bracket: z.enum(['under60', '60_79', '80plus'], { required_error: 'Select age bracket' }),
  other_income: z.number().min(0).default(0).optional(),
})

// Which fields belong to each step (for per-step validation trigger)
const STEP_FIELDS = [
  ['basic_salary', 'hra_received', 'lta', 'special_allowance', 'other_allowances', 'professional_tax'],
  ['investments_80c', 'health_insurance_self', 'health_insurance_parents', 'parent_senior_citizen', 'employee_nps_80ccd1b', 'employer_nps_80ccd2', 'home_loan_interest', 'savings_interest_80tta'],
  ['monthly_rent_paid', 'city_type'],
  ['age_bracket', 'other_income'],
  [], // review — no new fields
]

const TOTAL_STEPS = 5

/**
 * Props:
 *   onCalculationComplete (fn) — called with (profileId, taxResult)
 *   onCalculating (fn)         — called with bool
 */
export default function ManualWizard({ onCalculationComplete, onCalculating }) {
  const [step, setStep] = useState(0)
  const [apiError, setApiError] = useState(null)

  const {
    register,
    handleSubmit,
    trigger,
    getValues,
    control,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      basic_salary: undefined,
      hra_received: 0,
      lta: 0,
      special_allowance: 0,
      other_allowances: 0,
      professional_tax: 0,
      investments_80c: 0,
      health_insurance_self: 0,
      health_insurance_parents: 0,
      parent_senior_citizen: false,
      employee_nps_80ccd1b: 0,
      employer_nps_80ccd2: 0,
      home_loan_interest: 0,
      savings_interest_80tta: 0,
      monthly_rent_paid: 0,
      city_type: 'metro',
      age_bracket: 'under60',
      other_income: 0,
    },
    mode: 'onTouched',
  })

  const goNext = async () => {
    const fields = STEP_FIELDS[step]
    if (fields.length > 0) {
      const valid = await trigger(fields)
      if (!valid) return
    }
    if (step < TOTAL_STEPS - 1) setStep((s) => s + 1)
  }

  const goBack = () => {
    if (step > 0) setStep((s) => s - 1)
  }

  const onSubmit = async (data) => {
    setApiError(null)
    onCalculating?.(true)

    try {
      const payload = {
        ...data,
        input_method: 'manual',
        // Ensure NaN values (empty number inputs) become 0
        ...Object.fromEntries(
          Object.entries(data).map(([k, v]) => [k, typeof v === 'number' && isNaN(v) ? 0 : v]),
        ),
      }

      const profileResult = await createProfile(payload)
      const profileId = profileResult.profile_id

      const taxResult = await calculateTax(profileId)
      onCalculationComplete?.(profileId, taxResult)
    } catch (err) {
      onCalculating?.(false)
      const errData = err?.response?.data
      setApiError(errData ?? 'Calculation failed. Please try again.')
      toast.error('Something went wrong. Check your inputs.')
    }
  }

  const renderStep = () => {
    switch (step) {
      case 0: return <Step1Income register={register} errors={errors} />
      case 1: return <Step2Deductions register={register} errors={errors} control={control} />
      case 2: return <Step3Housing register={register} errors={errors} />
      case 3: return <Step4Other register={register} errors={errors} />
      case 4: return <Step5Review values={getValues()} />
      default: return null
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <WizardProgressBar currentStep={step} totalSteps={TOTAL_STEPS} />

      <ErrorBanner error={apiError} onDismiss={() => setApiError(null)} />

      <div className="min-h-[360px]">
        {renderStep()}
      </div>

      {/* Navigation */}
      <div className="mt-8 flex gap-3 pt-4 border-t border-gray-100">
        {step > 0 && (
          <button
            type="button"
            onClick={goBack}
            className="flex items-center gap-1.5 px-4 py-2.5 text-sm text-gray-600 border border-gray-300 rounded-xl hover:bg-gray-50 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            Back
          </button>
        )}

        {step < TOTAL_STEPS - 1 ? (
          <button
            type="button"
            onClick={goNext}
            className="ml-auto flex items-center gap-1.5 px-6 py-2.5 bg-navy text-white font-semibold text-sm rounded-xl hover:bg-navy-700 transition-colors"
          >
            Next
            <ChevronRight className="w-4 h-4" />
          </button>
        ) : (
          <button
            type="submit"
            className="ml-auto px-8 py-2.5 bg-amber hover:bg-yellow-400 text-navy font-bold text-sm rounded-xl transition-colors shadow-lg shadow-amber/20"
          >
            Analyse My Tax →
          </button>
        )}
      </div>
    </form>
  )
}
