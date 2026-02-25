import { useState } from 'react'

const FIELD_LABELS = {
  basic_salary: 'Basic Salary (Annual)',
  hra_received: 'HRA Received (Annual)',
  special_allowance: 'Special Allowance (Annual)',
  other_allowances: 'Other Allowances (Annual)',
  professional_tax: 'Professional Tax (Annual)',
  lta: 'Leave Travel Allowance',
  investments_80c: '80C Investments',
  health_insurance_self: '80D — Self & Family',
  health_insurance_parents: '80D — Parents',
  employee_nps_80ccd1b: 'NPS 80CCD(1B)',
  employer_nps_80ccd2: 'Employer NPS 80CCD(2)',
  home_loan_interest: 'Home Loan Interest 24(b)',
  savings_interest_80tta: 'Savings Interest 80TTA',
  other_income: 'Other Income',
}

/**
 * Renders the OCR extraction review grid.
 * Only shows successfully extracted (green/yellow) fields.
 * Red (not extracted) fields are hidden — users fill those in the manual wizard.
 *
 * Props:
 *   extractedFields  — { fieldName: { value, confidence } }
 *   onChange (fn)    — called with updated { fieldName: value } dict on each change
 */
export default function OCRFieldReview({ extractedFields, onChange }) {
  const [overrides, setOverrides] = useState({})

  const handleChange = (fieldName, value) => {
    const next = { ...overrides, [fieldName]: value }
    setOverrides(next)
    onChange?.(next)
  }

  if (!extractedFields || Object.keys(extractedFields).length === 0) {
    return (
      <p className="text-gray-500 text-sm text-center py-4">
        No fields were extracted. Please fill them in manually below.
      </p>
    )
  }

  // Only show green and yellow fields (successfully extracted)
  const visibleFields = Object.entries(extractedFields).filter(
    ([, fieldData]) => fieldData.confidence !== 'red'
  )

  if (visibleFields.length === 0) {
    return (
      <p className="text-gray-500 text-sm text-center py-4">
        No fields could be auto-filled. Please fill them in manually below.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {visibleFields.map(([fieldName, fieldData]) => {
          const currentValue = overrides[fieldName] ?? fieldData.value ?? ''
          const label = FIELD_LABELS[fieldName] ?? fieldName

          return (
            <div key={fieldName} className="rounded-lg border border-gray-200 bg-white p-3">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-medium text-gray-700">{label}</span>
              </div>
              <div className="relative">
                <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs">₹</span>
                <input
                  type="number"
                  min={0}
                  value={currentValue}
                  disabled
                  className="w-full pl-5 pr-2 py-1.5 text-sm rounded border cursor-not-allowed opacity-80 bg-transparent border-transparent focus:outline-none"
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
