import { Check } from 'lucide-react'

const STEP_LABELS = ['Income', 'Deductions', 'Housing', 'Other', 'Review']

/**
 * Props:
 *   currentStep (number, 0-indexed)
 *   totalSteps (number)
 */
export default function WizardProgressBar({ currentStep, totalSteps = 5 }) {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between">
        {STEP_LABELS.slice(0, totalSteps).map((label, i) => {
          const isDone = i < currentStep
          const isCurrent = i === currentStep

          return (
            <div key={i} className="flex flex-col items-center flex-1">
              <div className="flex items-center w-full">
                {/* Connector line (left) */}
                {i > 0 && (
                  <div
                    className={[
                      'flex-1 h-0.5 transition-colors',
                      i <= currentStep ? 'bg-navy' : 'bg-gray-200',
                    ].join(' ')}
                  />
                )}
                {/* Circle */}
                <div
                  className={[
                    'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300 flex-shrink-0',
                    isDone
                      ? 'bg-navy text-white'
                      : isCurrent
                        ? 'bg-navy text-white ring-4 ring-navy/20'
                        : 'bg-gray-200 text-gray-500',
                  ].join(' ')}
                >
                  {isDone ? <Check className="w-4 h-4" /> : i + 1}
                </div>
                {/* Connector line (right) */}
                {i < totalSteps - 1 && (
                  <div
                    className={[
                      'flex-1 h-0.5 transition-colors',
                      i < currentStep ? 'bg-navy' : 'bg-gray-200',
                    ].join(' ')}
                  />
                )}
              </div>
              <span
                className={[
                  'text-xs mt-1.5 font-medium',
                  isCurrent ? 'text-navy' : isDone ? 'text-navy/70' : 'text-gray-400',
                ].join(' ')}
              >
                {label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
