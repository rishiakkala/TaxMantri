import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, RotateCcw } from 'lucide-react'
import SavingsBanner from '../components/results/SavingsBanner.jsx'
import RegimeCardPair from '../components/results/RegimeCardPair.jsx'
import PDFDownloadButton from '../components/results/PDFDownloadButton.jsx'
import ITR1Table from '../components/results/ITR1Table.jsx'

/**
 * Results page — renders immediately from router state (no API refetch).
 * Profile ID from URL params is used for lazy PDF + ITR-1 mapping requests.
 *
 * Fallback: if user refreshes (router state lost), shows "Start Over" prompt.
 */
export default function ResultsPage() {
  const { profileId } = useParams()
  const { state } = useLocation()
  const navigate = useNavigate()

  const taxResult = state?.taxResult ?? null

  // ---- Fallback: page refresh lost router state ----
  if (!taxResult) {
    return (
      <div className="min-h-screen bg-[#f8fafc] flex items-center justify-center px-6">
        <div className="text-center max-w-sm">
          <div className="w-16 h-16 rounded-2xl bg-navy/10 flex items-center justify-center mx-auto mb-4">
            <RotateCcw className="w-8 h-8 text-navy/50" />
          </div>
          <h2 className="text-xl font-bold text-navy mb-2">Session Expired</h2>
          <p className="text-gray-500 text-sm mb-6">
            Your results aren't available after a page refresh. Please start over.
          </p>
          <button
            onClick={() => navigate('/input')}
            className="px-6 py-2.5 bg-navy text-white font-semibold rounded-xl hover:bg-navy-700 transition-colors"
          >
            Start Over
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#f8fafc]">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate('/input')}
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
          <span className="text-xs text-gray-400 bg-gray-100 px-2.5 py-1 rounded-full">
            AY 2025-26
          </span>
          <div className="ml-auto">
            <PDFDownloadButton profileId={profileId} />
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Title */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h1 className="text-2xl font-bold text-navy mb-1">Your Tax Analysis</h1>
          <p className="text-gray-500 text-sm">
            Old vs New Regime comparison for AY 2025-26. Click a card to see the full breakdown.
          </p>
        </motion.div>

        {/* Savings banner */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <SavingsBanner taxResult={taxResult} />
        </motion.div>

        {/* Regime cards */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <RegimeCardPair taxResult={taxResult} />
        </motion.div>

        {/* ITR-1 mapping (lazy) */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <ITR1Table profileId={profileId} />
        </motion.div>

        {/* Footer note */}
        <p className="text-center text-gray-400 text-xs pb-4">
          For educational purposes only. Consult a CA before filing ITR-1.
          Tax calculated on AY 2025-26 (FY 2024-25) rules.
        </p>
      </main>
    </div>
  )
}
