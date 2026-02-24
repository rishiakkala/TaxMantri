import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import InputTabs from '../components/input/InputTabs.jsx'
import LoadingOverlay from '../components/common/LoadingOverlay.jsx'
import Navbar from '../components/Navbar'

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
    <div className="min-h-screen font-sans text-custom-textDark relative">
      <LoadingOverlay visible={isCalculating} onComplete={handleOverlayComplete} />

      <Navbar />



      {/* Main content */}
      <main className="max-w-3xl mx-auto px-6 pt-32 pb-12">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-extrabold text-black mb-3 tracking-tight">
            Enter Your Tax Details
          </h1>
          <p className="text-gray-500 text-lg">
            Upload Form 16 for automatic extraction, or enter details manually.
          </p>
        </div>

        <div className="bg-white rounded-3xl border border-gray-100 shadow-[0_8px_30px_rgb(0,0,0,0.06)] p-6 md:p-10 relative overflow-hidden">
          {/* Subtle gradient blob behind form */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-custom-purple/5 rounded-full blur-3xl -z-10" />
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
