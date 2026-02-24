import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, User } from 'lucide-react'
import logoImage from '../images/justice_scales_black_gold.png'

import Navbar from '../components/Navbar'

const teamMembers = [
    {
        name: "amk",
        role: "Co-Founder & Developer",
        color: "bg-custom-purple/10",
        iconColor: "text-custom-purple"
    },
    {
        name: "chiru",
        role: "Co-Founder & Developer",
        color: "bg-custom-green/10",
        iconColor: "text-custom-green"
    },
    {
        name: "srikanth",
        role: "Co-Founder & Developer",
        color: "bg-amber-500/10",
        iconColor: "text-amber-500"
    },
    {
        name: "rishi",
        role: "Co-Founder & Developer",
        color: "bg-blue-500/10",
        iconColor: "text-blue-500"
    }
]

export default function AboutPage() {
    const navigate = useNavigate()

    return (
        <div className="min-h-screen font-sans text-custom-textDark overflow-x-hidden relative">
            <Navbar />

            {/* Main Content */}
            <main className="pt-36 pb-24 px-6 max-w-5xl mx-auto">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, ease: "easeOut" }}
                    className="text-center mb-16"
                >
                    <h1 className="text-5xl md:text-6xl font-extrabold text-black tracking-tight mb-4">
                        The Team Behind TaxMantri
                    </h1>
                    <p className="text-xl text-gray-500 max-w-2xl mx-auto font-medium">
                        We're on a mission to simplify tax filing for every salaried employee in India using smart, deterministic rule engines.
                    </p>
                </motion.div>

                {/* Team Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                    {teamMembers.map((member, idx) => (
                        <motion.div
                            key={member.name}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, delay: idx * 0.1 }}
                            className="group"
                        >
                            {/* Card Container */}
                            <div className="bg-white rounded-3xl p-6 border border-gray-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:shadow-[0_20px_40px_rgb(0,0,0,0.08)] transition-all duration-300 flex flex-col items-center">

                                {/* Image Placeholder Envelope */}
                                <div className={`w-32 h-32 rounded-full mb-6 relative overflow-hidden flex items-center justify-center ${member.color} border-4 border-white shadow-md group-hover:scale-105 transition-transform duration-300`}>
                                    {/* TODO: Replace this fallback icon with `<img src={...} className="w-full h-full object-cover" />` when user provides photos */}
                                    <User className={`w-12 h-12 ${member.iconColor} opacity-50`} strokeWidth={1.5} />
                                </div>

                                <h3 className="text-2xl font-extrabold text-black capitalize mb-1">{member.name}</h3>
                                <p className="text-sm font-semibold text-gray-400 tracking-wide uppercase">{member.role}</p>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </main>
        </div>
    )
}
