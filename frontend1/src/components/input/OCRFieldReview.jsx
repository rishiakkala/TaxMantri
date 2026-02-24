import { useState } from 'react'
import { CheckCircle, AlertCircle, XCircle } from 'lucide-react'

const CONFIDENCE_CONFIG = {
  green: {
    label: 'High confidence',
    icon: <CheckCircle className="w-4 h-4 text-success" />,
    badgeClass: 'bg-success-light text-success border-success/30',
    inputClass: 'border-green-300 bg-green-50',
    disabled: true,
  },
  yellow: {
    label: 'Review required',
    icon: <AlertCircle className="w-4 h-4 text-amber" />,
    badgeClass: 'bg-amber-50 text-amber border-amber/30',
    inputClass: 'border-amber/50 bg-amber-50',
    disabled: false,
  },
  red: {
    label: 'Not extracted',
    icon: <XCircle className="w-4 h-4 text-red-500" />,
    badgeClass: 'bg-red-50 text-red-600 border-red-200',
    inputClass: 'border-red-300 bg-red-50',
    disabled: false,
  },
}

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

  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600 mb-4">
        Review extracted fields. Green fields are locked (high confidence). Edit yellow and red fields.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {Object.entries(extractedFields).map(([fieldName, fieldData]) => {
          const confidence = fieldData.confidence ?? 'red'
          const config = CONFIDENCE_CONFIG[confidence] ?? CONFIDENCE_CONFIG.red
          const currentValue = overrides[fieldName] ?? fieldData.value ?? ''
          const label = FIELD_LABELS[fieldName] ?? fieldName

          return (
            <div key={fieldName} className={`rounded-lg border p-3 ${config.inputClass}`}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-medium text-gray-700">{label}</span>
                <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium ${config.badgeClass}`}>
                  {config.icon}
                  {confidence}
                </span>
              </div>
              <div className="relative">
                <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs">₹</span>
                <input
                  type="number"
                  min={0}
                  value={currentValue}
                  disabled={config.disabled}
                  onChange={(e) => handleChange(fieldName, Number(e.target.value))}
                  className={[
                    'w-full pl-5 pr-2 py-1.5 text-sm rounded border',
                    'focus:outline-none focus:ring-1 focus:ring-navy/30',
                    config.disabled
                      ? 'cursor-not-allowed opacity-80 bg-transparent border-transparent'
                      : 'bg-white border-gray-300',
                  ].join(' ')}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
