import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { RotateCcw } from 'lucide-react'
import SavingsBanner from '../components/results/SavingsBanner.jsx'
import AIInsightsCard from '../components/results/AIInsightsCard.jsx'
import RegimeCardPair from '../components/results/RegimeCardPair.jsx'
import PDFDownloadButton from '../components/results/PDFDownloadButton.jsx'
import ITR1Table from '../components/results/ITR1Table.jsx'
import Navbar from '../components/Navbar'

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

  // Persist profileId so ChatWidget can personalise answers with the current session
  useEffect(() => {
    if (profileId) localStorage.setItem('taxmantri_profile_id', profileId)
  }, [profileId])

  // ---- Fallback: page refresh lost router state ----
  if (!taxResult) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center px-6 font-sans">
        <div className="text-center max-w-sm">
          <div className="w-20 h-20 rounded-3xl bg-gray-50 flex items-center justify-center mx-auto mb-6 border border-gray-100 shadow-sm">
            <RotateCcw className="w-10 h-10 text-gray-400" />
          </div>
          <h2 className="text-3xl font-extrabold text-black mb-3">Session Expired</h2>
          <p className="text-gray-500 text-lg mb-8 font-medium">
            Your results aren't available after a page refresh. Please start over.
          </p>
          <button
            onClick={() => navigate('/input')}
            className="px-8 py-4 bg-custom-dark text-white font-bold text-lg rounded-full hover:bg-black transition-transform active:scale-95 shadow-xl shadow-black/10 w-full"
          >
            Start Over
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white font-sans text-custom-textDark overflow-x-hidden">
      <Navbar />

      {/* Floating Action Button for PDF - positioned below navbar on mobile, or absolute top-right */}
      <div className="fixed top-4 right-6 w-auto z-50 pointer-events-auto mt-2">
        <PDFDownloadButton profileId={profileId} />
      </div>

      {/* Main content */}
      <main className="max-w-4xl mx-auto px-6 pt-32 pb-16 space-y-8">
        {/* Title */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h1 className="text-4xl font-extrabold text-black mb-2 tracking-tight">Your Tax Analysis</h1>
          <p className="text-gray-500 text-lg font-medium">
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

        {/* AI Insights — rationale, IT Act citations, law context */}
        <AIInsightsCard taxResult={taxResult} />

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
