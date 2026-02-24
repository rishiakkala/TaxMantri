import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, ChevronDown, ChevronUp, BookOpen, Scale, TrendingDown } from 'lucide-react'

// ---- Helpers ----------------------------------------------------------------
const INR = (v) => '₹' + Math.abs(Number(v ?? 0)).toLocaleString('en-IN')

// Maps DeductionBreakdown field keys → human label + IT Act section
const SECTION_MAP = {
    standard_deduction: { label: 'Standard Deduction', section: 'Sec 16(ia)' },
    hra_exemption: { label: 'HRA Exemption', section: 'Rule 2A' },
    section_80c: { label: '80C Investments', section: 'Sec 80C' },
    section_80d: { label: 'Health Insurance', section: 'Sec 80D' },
    section_80ccd1b: { label: 'NPS (Employee)', section: 'Sec 80CCD(1B)' },
    section_80ccd2: { label: 'NPS (Employer)', section: 'Sec 80CCD(2)' },
    section_80tta_ttb: { label: 'Savings Interest', section: 'Sec 80TTA/TTB' },
    section_24b: { label: 'Home Loan Interest', section: 'Sec 24(b)' },
    professional_tax: { label: 'Professional Tax', section: 'Sec 16(iii)' },
}

// Calculation flow steps
function CalcFlow({ regime }) {
    if (!regime) return null
    const steps = [
        { label: 'Gross Income', value: regime.gross_income },
        { label: 'Deductions', value: regime.total_deductions, minus: true },
        { label: 'Taxable Income', value: regime.taxable_income },
        { label: 'Income Tax', value: regime.tax_before_cess },
        { label: '+ Health Cess', value: regime.cess },
        { label: 'Final Tax', value: regime.total_tax, highlight: true },
    ]

    return (
        <div className="flex flex-wrap gap-0 items-stretch mb-5">
            {steps.map((s, i) => (
                <div key={i} className="flex items-center">
                    <div className={`flex flex-col items-center px-3 py-2 rounded-xl ${s.highlight ? 'bg-purple-600 text-white' : 'bg-gray-50 border border-gray-100'}`}>
                        <span className={`text-xs font-semibold ${s.highlight ? 'text-purple-200' : 'text-gray-400'}`}>
                            {s.label}
                        </span>
                        <span className={`text-sm font-extrabold mt-0.5 ${s.highlight ? 'text-white' : s.minus ? 'text-red-500' : 'text-gray-800'}`}>
                            {s.minus ? '−' : ''}{INR(s.value)}
                        </span>
                    </div>
                    {i < steps.length - 1 && (
                        <span className="text-gray-300 font-light text-base px-1">→</span>
                    )}
                </div>
            ))}
        </div>
    )
}

// Deduction breakdown rows — only non-zero
function DeductionTable({ breakdown }) {
    if (!breakdown) return null
    const rows = Object.entries(breakdown)
        .filter(([key, val]) => val > 0 && SECTION_MAP[key])
        .map(([key, val]) => ({ ...SECTION_MAP[key], amount: val }))

    if (rows.length === 0) return null

    return (
        <div className="mb-5">
            <div className="flex items-center gap-1.5 mb-2.5">
                <TrendingDown className="w-3.5 h-3.5 text-purple-500" />
                <span className="text-xs font-bold text-purple-700 uppercase tracking-wider">
                    Deductions Applied
                </span>
            </div>
            <div className="rounded-2xl border border-purple-100 overflow-hidden">
                <table className="w-full text-xs">
                    <thead>
                        <tr className="bg-purple-50">
                            <th className="text-left px-3 py-2 text-gray-500 font-bold">Deduction</th>
                            <th className="text-left px-3 py-2 text-gray-500 font-bold">IT Act Section</th>
                            <th className="text-right px-3 py-2 text-gray-500 font-bold">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((r, i) => (
                            <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-purple-50/40'}>
                                <td className="px-3 py-2 text-gray-700 font-semibold">{r.label}</td>
                                <td className="px-3 py-2">
                                    <span className="bg-purple-100 text-purple-700 font-bold px-2 py-0.5 rounded-full">
                                        {r.section}
                                    </span>
                                </td>
                                <td className="px-3 py-2 text-right text-green-700 font-extrabold">
                                    {INR(r.amount)}
                                </td>
                            </tr>
                        ))}
                        {/* Total row */}
                        <tr className="bg-purple-50 border-t border-purple-200">
                            <td className="px-3 py-2 font-bold text-gray-800" colSpan={2}>Total Deductions</td>
                            <td className="px-3 py-2 text-right font-extrabold text-purple-700">
                                {INR(rows.reduce((s, r) => s + r.amount, 0))}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    )
}

// ---- Main Component ---------------------------------------------------------
/**
 * AIInsightsCard — LLM rationale + IT Act citations + calculation summary.
 * Props:
 *   taxResult — full TaxResult from backend
 */
export default function AIInsightsCard({ taxResult }) {
    const [lawExpanded, setLawExpanded] = useState(false)

    if (!taxResult) return null

    const { rationale, citations = [], law_context = '', recommended_regime, old_regime, new_regime } = taxResult

    const recRegime = recommended_regime === 'old' ? old_regime : new_regime
    const breakdown = recRegime?.deduction_breakdown
    const regimeLabel = recommended_regime === 'old' ? 'Old Regime' : 'New Regime'

    // Render if there's any content at all
    const hasContent = rationale || citations.length > 0 || law_context || recRegime
    if (!hasContent) return null

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
                    <p className="text-xs text-gray-400 font-medium">
                        Powered by Mistral · Grounded in Income Tax Act · {regimeLabel} breakdown
                    </p>
                </div>
            </div>

            {/* Rationale */}
            {rationale && (
                <div className="mb-5">
                    <p className="text-gray-700 text-sm leading-relaxed font-medium">{rationale}</p>
                </div>
            )}

            {/* Divider */}
            <div className="border-t border-purple-100 my-4" />

            {/* Calculation flow */}
            {recRegime && (
                <>
                    <div className="flex items-center gap-1.5 mb-3">
                        <span className="text-xs font-bold text-purple-700 uppercase tracking-wider">
                            {regimeLabel} — Calculation Breakdown
                        </span>
                    </div>
                    <CalcFlow regime={recRegime} />
                </>
            )}

            {/* Deduction breakdown table */}
            <DeductionTable breakdown={breakdown} />

            {/* Citation badges */}
            {citations.length > 0 && (
                <div className="mb-5">
                    <div className="flex items-center gap-1.5 mb-2.5">
                        <Scale className="w-3.5 h-3.5 text-purple-500" />
                        <span className="text-xs font-bold text-purple-700 uppercase tracking-wider">
                            Referenced IT Act Sections
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
                        <span>View Full Legal Context</span>
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
