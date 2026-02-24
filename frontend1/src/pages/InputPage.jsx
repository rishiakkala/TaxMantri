import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import InputTabs from '../components/input/InputTabs.jsx'
import LoadingOverlay from '../components/common/LoadingOverlay.jsx'

/**
 * The state bridge between InputTabs and ResultsPage.
 *
 * Flow:
 *   1. Child tab calls onCalculationComplete(profileId, taxResult)
 *   2. InputPage stores {profileId, taxResult} in pendingNavigation
 *   3. Shows LoadingOverlay
 *   4. LoadingOverlay.onComplete fires → navigate to /results/:id
 *      passing taxResult as router state (no refetch needed)
 */
export default function InputPage() {
  const navigate = useNavigate()
  const [isCalculating, setIsCalculating] = useState(false)
  const [pendingNavigation, setPendingNavigation] = useState(null)

  const handleCalculationComplete = useCallback((profileId, taxResult) => {
    setPendingNavigation({ profileId, taxResult })
    setIsCalculating(true)
  }, [])

  const handleOverlayComplete = useCallback(() => {
    if (pendingNavigation) {
      navigate(`/results/${pendingNavigation.profileId}`, {
        state: { taxResult: pendingNavigation.taxResult },
      })
    }
  }, [navigate, pendingNavigation])

  return (
    <div className="min-h-screen bg-[#f8fafc]">
      <LoadingOverlay visible={isCalculating} onComplete={handleOverlayComplete} />

      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-6 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="text-gray-500 hover:text-navy transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-navy flex items-center justify-center">
              <span className="text-amber font-bold text-xs">₹</span>
            </div>
            <span className="font-bold text-navy">TaxMantri</span>
          </div>
          <span className="ml-auto text-xs text-gray-400 bg-gray-100 px-2.5 py-1 rounded-full">
            AY 2025-26
          </span>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-2xl mx-auto px-6 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-navy mb-1">
            Enter Your Tax Details
          </h1>
          <p className="text-gray-500 text-sm">
            Upload Form 16 for automatic extraction, or enter details manually.
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <InputTabs
            onCalculationComplete={handleCalculationComplete}
            onCalculating={setIsCalculating}
          />
        </div>

        <p className="text-center text-gray-400 text-xs mt-6">
          Your data stays in your browser session only. No account required.
        </p>
      </main>
    </div>
  )
}
