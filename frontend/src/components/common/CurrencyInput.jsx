import { forwardRef } from 'react'

/**
 * ₹-prefixed currency number input.
 *
 * Props (in addition to standard HTML input props):
 *   label     (string)  — field label above
 *   error     (string)  — validation error message below
 *   helpText  (string)  — subtle helper below field
 *   required  (bool)    — shows asterisk on label
 */
const CurrencyInput = forwardRef(function CurrencyInput(
  { label, error, helpText, required, className = '', ...props },
  ref,
) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-sm font-medium text-gray-700">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 font-medium text-sm select-none">
          ₹
        </span>
        <input
          ref={ref}
          type="number"
          min={0}
          step={1}
          className={[
            'w-full pl-7 pr-3 py-2.5 rounded-lg border text-sm transition-colors',
            'focus:outline-none focus:ring-2 focus:ring-navy/30 focus:border-navy',
            error
              ? 'border-red-400 bg-red-50 text-red-900'
              : 'border-gray-300 bg-white text-gray-900 hover:border-gray-400',
            className,
          ].join(' ')}
          {...props}
        />
      </div>
      {error && (
        <p className="text-red-600 text-xs">{error}</p>
      )}
      {helpText && !error && (
        <p className="text-gray-500 text-xs">{helpText}</p>
      )}
    </div>
  )
})

export default CurrencyInput
