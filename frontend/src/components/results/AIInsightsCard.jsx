import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, ChevronDown, ChevronUp, BookOpen, Scale } from 'lucide-react'

/**
 * AIInsightsCard — displays LLM-generated tax analysis from the agentic pipeline.
 *
 * Props:
 *   taxResult — full TaxResult from backend (expects rationale, citations, law_context)
 */
export default function AIInsightsCard({ taxResult }) {
    const [lawExpanded, setLawExpanded] = useState(false)

    if (!taxResult) return null

    const { rationale, citations = [], law_context = '' } = taxResult

    // Only render if we have actual LLM content beyond the rule-based default
    if (!rationale && citations.length === 0 && !law_context) return null

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.4 }}
            className="rounded-3xl border border-purple-100 bg-gradient-to-br from-purple-50/60 to-white p-6 shadow-sm"
        >
            {/* Header */}
            <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-2xl bg-purple-600 flex items-center justify-center flex-shrink-0 shadow-md shadow-purple-200">
                    <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                    <h2 className="text-base font-extrabold text-black tracking-tight">AI Tax Insights</h2>
                    <p className="text-xs text-gray-400 font-medium">Powered by Mistral · grounded in Income Tax Act</p>
                </div>
            </div>

            {/* Rationale */}
            {rationale && (
                <div className="mb-5">
                    <p className="text-gray-700 text-sm leading-relaxed font-medium">{rationale}</p>
                </div>
            )}

            {/* Citation badges */}
            {citations.length > 0 && (
                <div className="mb-5">
                    <div className="flex items-center gap-1.5 mb-2.5">
                        <Scale className="w-3.5 h-3.5 text-purple-500" />
                        <span className="text-xs font-bold text-purple-700 uppercase tracking-wider">
                            Applicable IT Act Sections
                        </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {citations.map((c, i) => (
                            <span
                                key={i}
                                className="inline-flex items-center px-3 py-1 rounded-full bg-purple-100 text-purple-800 text-xs font-bold border border-purple-200"
                                title={c.excerpt || ''}
                            >
                                {c.section || `Section ${i + 1}`}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Collapsible law context */}
            {law_context && (
                <div className="border-t border-purple-100 pt-4">
                    <button
                        onClick={() => setLawExpanded(v => !v)}
                        className="flex items-center gap-2 text-xs font-bold text-purple-600 hover:text-purple-800 transition-colors w-full text-left"
                    >
                        <BookOpen className="w-3.5 h-3.5" />
                        <span>View Legal Context</span>
                        {lawExpanded
                            ? <ChevronUp className="w-3.5 h-3.5 ml-auto" />
                            : <ChevronDown className="w-3.5 h-3.5 ml-auto" />
                        }
                    </button>

                    <AnimatePresence>
                        {lawExpanded && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                transition={{ duration: 0.25 }}
                                className="overflow-hidden"
                            >
                                <p className="mt-3 text-xs text-gray-500 leading-relaxed whitespace-pre-line bg-gray-50 rounded-xl p-4 border border-gray-100">
                                    {law_context}
                                </p>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            )}
        </motion.div>
    )
}
