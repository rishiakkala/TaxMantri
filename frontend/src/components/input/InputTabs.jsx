import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, PenLine } from 'lucide-react'
import UploadTab from './UploadTab.jsx'
import ManualWizard from './ManualWizard.jsx'

const TABS = [
  { id: 'upload', label: 'Upload Form 16', icon: <Upload className="w-4 h-4" /> },
  { id: 'manual', label: 'Manual Entry', icon: <PenLine className="w-4 h-4" /> },
]

/**
 * Props:
 *   onCalculationComplete (fn) — passed through to child tabs
 *   onCalculating (fn)         — passed through to child tabs
 */
export default function InputTabs({ onCalculationComplete, onCalculating }) {
  const [activeTab, setActiveTab] = useState('upload')

  return (
    <div>
      {/* Tab switcher */}
      <div className="flex rounded-2xl bg-gray-100/80 p-1.5 mb-8">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={[
              'flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-bold transition-all duration-200',
              activeTab === tab.id
                ? 'bg-white text-black shadow-md'
                : 'text-gray-500 hover:text-custom-purple hover:bg-white/50',
            ].join(' ')}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, x: activeTab === 'upload' ? -12 : 12 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: activeTab === 'upload' ? 12 : -12 }}
          transition={{ duration: 0.2 }}
        >
          {activeTab === 'upload' ? (
            <UploadTab
              onCalculationComplete={onCalculationComplete}
              onCalculating={onCalculating}
            />
          ) : (
            <ManualWizard
              onCalculationComplete={onCalculationComplete}
              onCalculating={onCalculating}
            />
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
