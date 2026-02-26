import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, CheckCircle2, FileText, Settings, ShieldCheck, Zap, BarChart, FileCheck, Download } from 'lucide-react'
import logoImage from '../images/justice_scales_black_gold.png'

import Navbar from '../components/Navbar'

const steps = [
    {
        icon: <Settings className="w-8 h-8 text-custom-purple" />,
        title: "Choose How You Want to Start",
        description: "TaxMantri supports two easy paths, ensuring flexibility for every user.",
        options: [
            { title: "Upload Form 16", desc: "The system uses OCR to extract salary details automatically." },
            { title: "Enter Details Manually", desc: "A guided 5-step wizard helps you enter salary, HRA, investments, and more." }
        ],
        color: "bg-custom-purple/10 border-custom-purple/20"
    },
    {
        icon: <FileText className="w-8 h-8 text-amber-500" />,
        title: "Smart Data Extraction & Validation",
        description: "If you upload Form 16, our OCR reads your document, extracting key fields like salary, HRA, and TDS making it easier for the user.",
        color: "bg-amber-500/10 border-amber-500/20"
    },
    {
        icon: <BarChart className="w-8 h-8 text-custom-green" />,
        title: "Your Financial Profile is Built",
        description: "Once your data is confirmed, TaxMantri creates a structured financial profile including salary components, HRA, investments, health insurance, and loan interest. This standardized profile powers all calculations.",
        color: "bg-custom-green/10 border-custom-green/20"
    },
    {
        icon: <Zap className="w-8 h-8 text-blue-500" />,
        title: "Deterministic Tax Engine",
        description: "TaxMantri uses a pure rule-based tax engine (not AI) to ensure legal accuracy. It calculates both the Old Tax Regime (HRA, standard deduction, 80C/80D, 87A) and the New Tax Regime. The system then recommends the regime with the lowest tax.",
        color: "bg-blue-500/10 border-blue-500/20"
    },
    {
        icon: <CheckCircle2 className="w-8 h-8 text-pink-500" />,
        title: "Regime Comparison & Optimizer",
        description: "Instantly see what saves more with side-by-side cards showing total payable, effective savings, and deduction breakdown. Our optimizer identifies unused deductions—like showing you 'Invest ₹38,000 more under 80C to save ₹11,400'.",
        color: "bg-pink-500/10 border-pink-500/20"
    },
    {
        icon: <ShieldCheck className="w-8 h-8 text-indigo-500" />,
        title: "Privacy & Security First",
        description: "Built with strong security. Files are stored in cache memory and destroyed after 15 minutes or after session termination. No raw data is sent to external APIs, and all transmissions are secure (TLS). Your data stays safe.",
        color: "bg-indigo-500/10 border-indigo-500/20"
    }
]

export default function HowItWorksPage() {
    const navigate = useNavigate()

    return (
        <div className="min-h-screen font-sans text-custom-textDark relative">
            <Navbar />

            {/* Hero Section */}
            <main className="pt-36 pb-16 px-6 max-w-4xl mx-auto text-center">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.7, ease: "easeOut" }}
                >
                    <div className="inline-flex items-center gap-2 bg-custom-green/20 text-custom-green font-bold px-4 py-2 rounded-full mb-6 border border-custom-green/30">
                        Your AI Tax Co-Pilot
                    </div>
                    <h1 className="text-5xl md:text-6xl font-extrabold text-black leading-tight tracking-tight mb-6">
                        From Form 16 to Filing, <br className="hidden md:block" /> in Minutes
                    </h1>
                    <p className="text-xl text-gray-600 max-w-2xl mx-auto font-medium leading-relaxed">
                        TaxMantri simplifies income tax filing for salaried individuals by converting complex tax rules into clear, actionable guidance.
                    </p>
                </motion.div>
            </main>

            {/* Animated Steps Timeline */}
            <section className="px-6 pb-24 max-w-4xl mx-auto">
                <div className="space-y-12 relative">
                    {/* Subtle line connecting steps */}
                    <div className="hidden md:block absolute left-12 top-10 bottom-10 w-px bg-gray-200" />

                    {steps.map((step, idx) => (
                        <motion.div
                            key={idx}
                            initial={{ opacity: 0, x: -20, y: 20 }}
                            whileInView={{ opacity: 1, x: 0, y: 0 }}
                            viewport={{ once: true, margin: "-100px" }}
                            transition={{ duration: 0.5, delay: idx * 0.1 }}
                            className="relative flex flex-col md:flex-row gap-6 md:gap-10"
                        >
                            {/* Icon / Number Indicator */}
                            <div className="md:w-24 shrink-0 flex flex-col items-center">
                                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center bg-white border shadow-md relative z-10 ${step.color}`}>
                                    {step.icon}
                                </div>
                            </div>

                            {/* Content Card */}
                            <div className="flex-1 bg-white border border-gray-100 rounded-3xl p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-shadow">
                                <div className="flex items-center gap-4 mb-4">
                                    <span className="text-4xl font-extrabold text-gray-100 select-none">0{idx + 1}</span>
                                    <h3 className="text-2xl font-bold bg-clip-text text-black">{step.title}</h3>
                                </div>

                                <p className="text-gray-600 leading-relaxed text-lg mb-6">
                                    {step.description}
                                </p>

                                {step.options && (
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
                                        {step.options.map((opt, i) => (
                                            <div key={i} className="bg-gray-50 rounded-2xl p-5 border border-gray-100">
                                                <h4 className="font-bold text-gray-900 mb-2">{opt.title}</h4>
                                                <p className="text-sm text-gray-600">{opt.desc}</p>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    ))}
                </div>
            </section>

            {/* CTA Footer */}
            <section className="bg-custom-dark text-white py-20 px-6 text-center">
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5 }}
                >
                    <h2 className="text-4xl font-extrabold mb-6">Tax smarter, Save better.</h2>
                    <p className="text-gray-400 mb-10 max-w-xl mx-auto text-lg">
                        Ready to turn tax filing from guesswork into guided, accurate, and optimized decision-making?
                    </p>
                    <button
                        onClick={() => navigate('/input')}
                        className="bg-black/60 backdrop-blur-md border border-white/20 hover:bg-black/80 text-white font-bold text-lg px-8 py-4 rounded-full transition-all duration-300 active:scale-95 shadow-[0_4px_16px_rgba(0,0,0,0.2)] hover:shadow-[0_8px_24px_rgba(0,0,0,0.3)]"
                    >
                        Calculate Your Tax Now
                    </button>
                </motion.div>
            </section>
        </div>
    )
}
