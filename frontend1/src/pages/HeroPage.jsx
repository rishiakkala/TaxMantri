import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Shield, Zap, FileText } from 'lucide-react'

const features = [
  {
    icon: <FileText className="w-6 h-6" />,
    title: 'Form 16 OCR',
    desc: 'Upload your Form 16 — we extract all fields automatically.',
  },
  {
    icon: <Zap className="w-6 h-6" />,
    title: 'Instant Comparison',
    desc: 'Old vs New Regime — calculated to the rupee, instantly.',
  },
  {
    icon: <Shield className="w-6 h-6" />,
    title: 'CA-Verified Engine',
    desc: '50+ test cases. Deterministic. No LLM guesswork in tax math.',
  },
]

export default function HeroPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gradient-to-br from-navy-600 via-navy-500 to-[#2867a8] flex flex-col">
      {/* Nav */}
      <nav className="px-8 py-5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-amber flex items-center justify-center">
            <span className="text-navy font-bold text-sm">₹</span>
          </div>
          <span className="text-white font-bold text-xl tracking-tight">TaxMantri</span>
        </div>
        <span className="text-navy-200 text-sm">AY 2025-26</span>
      </nav>

      {/* Hero content */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 bg-white/10 text-white text-xs font-medium px-3 py-1.5 rounded-full mb-6 border border-white/20">
            <span className="w-2 h-2 rounded-full bg-amber animate-pulse" />
            Free for AY 2025-26 · ITR-1 Salaried Individuals
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold text-white leading-tight tracking-tight mb-6">
            Your ITR-1{' '}
            <span className="text-amber">Tax Co-Pilot</span>
          </h1>

          <p className="text-navy-100 text-lg md:text-xl max-w-2xl mx-auto mb-10 leading-relaxed">
            Upload your Form 16 or enter details manually. Get an instant Old vs New
            Regime comparison with deduction breakdown — calculated precisely, not estimated.
          </p>

          <motion.button
            onClick={() => navigate('/input')}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
            className="inline-flex items-center gap-3 bg-amber hover:bg-yellow-400 text-navy font-bold text-lg px-8 py-4 rounded-2xl shadow-2xl shadow-amber/30 transition-colors"
          >
            Calculate My Tax
            <ArrowRight className="w-5 h-5" />
          </motion.button>

          <p className="text-navy-200 text-sm mt-4">No login required · Results in seconds</p>
        </motion.div>

        {/* Feature cards */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl w-full"
        >
          {features.map((f, i) => (
            <div
              key={i}
              className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-6 text-left hover:bg-white/15 transition-colors"
            >
              <div className="text-amber mb-3">{f.icon}</div>
              <h3 className="text-white font-semibold mb-1">{f.title}</h3>
              <p className="text-navy-200 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </motion.div>
      </div>

      {/* Footer */}
      <footer className="py-6 text-center text-navy-300 text-xs">
        For educational purposes only. Consult a CA for filing advice.
      </footer>
    </div>
  )
}
