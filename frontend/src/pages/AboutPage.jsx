import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import logoImage from '../images/justice_scales_black_gold.png'
import amkImg from '../images/amk.jpeg'
import chiruImg from '../images/chiru.jpeg'
import srikanthImg from '../images/srikanth.jpeg'
import rishiImg from '../images/rishi.jpeg'

const teamMembers = [
    {
        name: "amk",
        role: "Co-Founder & Developer",
        image: amkImg,
    },
    {
        name: "chiru",
        role: "Co-Founder & Developer",
        image: chiruImg,
    },
    {
        name: "srikanth",
        role: "Co-Founder & Developer",
        image: srikanthImg,
    },
    {
        name: "rishi",
        role: "Co-Founder & Developer",
        image: rishiImg,
    }
]

export default function AboutPage() {
    const navigate = useNavigate()

    return (
        <div className="min-h-screen bg-white font-sans text-custom-textDark overflow-x-hidden">
            {/* Minimal Logo Positioned Top-Left */}
            <div className="fixed top-0 left-0 w-full z-50 px-6 py-6 pointer-events-none">
                <button onClick={() => navigate('/')} className="flex items-center gap-2 pointer-events-auto group">
                    <img src={logoImage} alt="TaxMantri Logo" className="h-9 w-auto object-contain group-hover:scale-105 transition-transform" />
                    <span className="font-extrabold text-2xl tracking-tighter text-black group-hover:text-custom-purple transition-colors">TaxMantri</span>
                </button>
            </div>

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
                                <div className="w-32 h-32 rounded-full mb-6 relative overflow-hidden border-4 border-white shadow-md group-hover:scale-105 transition-transform duration-300">
                                    <img
                                        src={member.image}
                                        alt={member.name}
                                        className="w-full h-full object-cover"
                                    />
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
