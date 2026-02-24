import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import RegimeCard from './RegimeCard.jsx'
import DetailPanel from './DetailPanel.jsx'

/**
 * Orchestrates the regime card grid + expand animation.
 *
 * Default:   grid-cols-2 (both cards side by side)
 * Old open:  grid-cols-[280px_1fr] (card left, detail right)
 * New open:  grid-cols-[1fr_280px] (detail left, card right)
 *
 * Props:
 *   taxResult — full TaxResult from backend
 */
export default function RegimeCardPair({ taxResult }) {
  const [expandedRegime, setExpandedRegime] = useState(null)

  if (!taxResult) return null

  const { old_regime, new_regime, recommended_regime } = taxResult

  const toggleRegime = (regime) => {
    setExpandedRegime((prev) => (prev === regime ? null : regime))
  }

  const isOldExpanded = expandedRegime === 'old'
  const isNewExpanded = expandedRegime === 'new'

  // Determine grid layout
  const gridClass = isOldExpanded
    ? 'grid-cols-[280px_1fr]'
    : isNewExpanded
      ? 'grid-cols-[1fr_280px]'
      : 'grid-cols-2'

  return (
    <motion.div
      layout
      className={`grid gap-4 ${gridClass}`}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
    >
      {/* OLD REGIME column */}
      {isNewExpanded ? (
        // Detail panel shows on left when new is expanded
        <AnimatePresence mode="sync">
          <DetailPanel
            key="new-detail"
            regime="new"
            data={new_regime}
            taxResult={taxResult}
            side="left"
            onClose={() => setExpandedRegime(null)}
          />
        </AnimatePresence>
      ) : (
        <RegimeCard
          regime="old"
          data={old_regime}
          isRecommended={recommended_regime === 'old'}
          isExpanded={isOldExpanded}
          onClick={() => toggleRegime('old')}
        />
      )}

      {/* NEW REGIME column */}
      {isOldExpanded ? (
        // Detail panel shows on right when old is expanded
        <AnimatePresence mode="sync">
          <DetailPanel
            key="old-detail"
            regime="old"
            data={old_regime}
            taxResult={taxResult}
            side="right"
            onClose={() => setExpandedRegime(null)}
          />
        </AnimatePresence>
      ) : (
        <RegimeCard
          regime="new"
          data={new_regime}
          isRecommended={recommended_regime === 'new'}
          isExpanded={isNewExpanded}
          onClick={() => toggleRegime('new')}
        />
      )}
    </motion.div>
  )
}
