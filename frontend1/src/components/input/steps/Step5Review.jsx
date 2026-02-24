const INR = (v) =>
  v == null || isNaN(v)
    ? '₹0'
    : '₹' + Number(v).toLocaleString('en-IN')

const SECTIONS = [
  {
    title: 'Income',
    fields: [
      { key: 'basic_salary', label: 'Basic Salary' },
      { key: 'hra_received', label: 'HRA Received' },
      { key: 'lta', label: 'LTA' },
      { key: 'special_allowance', label: 'Special Allowance' },
      { key: 'other_allowances', label: 'Other Allowances' },
      { key: 'professional_tax', label: 'Professional Tax' },
      { key: 'other_income', label: 'Other Income' },
    ],
  },
  {
    title: 'Deductions',
    fields: [
      { key: 'investments_80c', label: '80C Investments' },
      { key: 'health_insurance_self', label: '80D Self & Family' },
      { key: 'health_insurance_parents', label: '80D Parents' },
      { key: 'employee_nps_80ccd1b', label: 'NPS 80CCD(1B)' },
      { key: 'employer_nps_80ccd2', label: 'NPS 80CCD(2)' },
      { key: 'home_loan_interest', label: 'Home Loan Interest' },
      { key: 'savings_interest_80tta', label: 'Savings Interest' },
    ],
  },
  {
    title: 'Housing',
    fields: [
      { key: 'monthly_rent_paid', label: 'Monthly Rent' },
    ],
  },
]

/**
 * Step 5 — Read-only review of all entered values.
 * Props:
 *   values — all form values from getValues()
 */
export default function Step5Review({ values }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-navy mb-1">Review Your Details</h2>
        <p className="text-gray-500 text-sm">
          Check everything below before we calculate your tax. Go back to any step to make changes.
        </p>
      </div>

      {SECTIONS.map((section) => {
        const filledFields = section.fields.filter(
          (f) => values?.[f.key] != null && Number(values[f.key]) !== 0,
        )
        if (filledFields.length === 0) return null

        return (
          <div key={section.title} className="rounded-xl border border-gray-200 overflow-hidden">
            <div className="bg-gray-50 px-4 py-2.5 border-b border-gray-200">
              <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
                {section.title}
              </span>
            </div>
            <div className="divide-y divide-gray-100">
              {filledFields.map((f) => (
                <div key={f.key} className="flex justify-between items-center px-4 py-3">
                  <span className="text-sm text-gray-700">{f.label}</span>
                  <span className="text-sm font-semibold text-navy">
                    {f.key === 'monthly_rent_paid'
                      ? `${INR(values[f.key])}/mo`
                      : INR(values[f.key])}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )
      })}

      {/* Profile metadata */}
      <div className="rounded-xl border border-gray-200 overflow-hidden">
        <div className="bg-gray-50 px-4 py-2.5 border-b border-gray-200">
          <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Profile</span>
        </div>
        <div className="divide-y divide-gray-100">
          <div className="flex justify-between items-center px-4 py-3">
            <span className="text-sm text-gray-700">City Type</span>
            <span className="text-sm font-semibold text-navy capitalize">
              {values?.city_type === 'metro' ? 'Metro' : 'Non-Metro'}
            </span>
          </div>
          <div className="flex justify-between items-center px-4 py-3">
            <span className="text-sm text-gray-700">Age Bracket</span>
            <span className="text-sm font-semibold text-navy">
              {values?.age_bracket === 'under60' ? 'Under 60'
                : values?.age_bracket === '60_79' ? '60–79 (Senior)'
                : '80+ (Super Senior)'}
            </span>
          </div>
          {values?.parent_senior_citizen && (
            <div className="flex justify-between items-center px-4 py-3">
              <span className="text-sm text-gray-700">Parent Status</span>
              <span className="text-sm font-semibold text-navy">Senior Citizen</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
