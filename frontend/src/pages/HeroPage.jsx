import { useNavigate } from 'react-router-dom'
import { motion, useScroll, useTransform } from 'framer-motion'
import { ArrowRight, Star, User, Code } from 'lucide-react'
import { useRef } from 'react'
import heroImage from '../images/Gemini_Generated_Image_m5ixi9m5ixi9m5ix.png'
import logoImage from '../images/justice_scales_black_gold.png'

import Navbar from '../components/Navbar'

export default function HeroPage() {
  const navigate = useNavigate()
  const scrollRef = useRef(null)
  const { scrollYProgress } = useScroll({
    target: scrollRef,
    offset: ["start end", "end start"]
  })

  // A subtle parallax/scale effect for the purple container based on scroll
  const purpleScale = useTransform(scrollYProgress, [0, 0.5], [0.95, 1])

  return (
    <div className="min-h-screen font-sans text-custom-textDark overflow-x-hidden relative">
      {/* Animated Background */}
      <div className="fixed inset-0 w-full h-full pointer-events-none -z-10 overflow-hidden bg-gradient-to-br from-[#cbe0f5] to-[#aaccf0]">
        {/* Floating Circle 1 */}
        <motion.div
          animate={{ y: [0, -50, 0], x: [0, 20, 0] }}
          transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-[5%] left-[-5%] w-80 h-80 bg-blue-300 rounded-full blur-[100px] opacity-70"
        />
        {/* Floating Circle 2 */}
        <motion.div
          animate={{ y: [0, 50, 0], x: [0, -30, 0] }}
          transition={{ duration: 9, repeat: Infinity, ease: "easeInOut", delay: 1 }}
          className="absolute top-[40%] right-[-10%] w-[500px] h-[500px] bg-cyan-200 rounded-full blur-[120px] opacity-40"
        />
        {/* Floating Circle 3 */}
        <motion.div
          animate={{ y: [0, -40, 0], x: [0, 40, 0] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut", delay: 2 }}
          className="absolute bottom-[-10%] left-[20%] w-96 h-96 bg-blue-400 rounded-full blur-[120px] opacity-20"
        />
      </div>

      {/* Translucent Navigation Tab */}
      <Navbar />

      {/* Hero Section */}
      <main className="pt-36 pb-20 px-6 max-w-7xl mx-auto flex flex-col items-center text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
        >
          <h1
            style={{ fontFamily: "'Quicksand', sans-serif" }}
            className="text-6xl md:text-[5.5rem] font-extrabold leading-[1.05] tracking-tight mb-6 relative inline-block z-10"
          >
            <span className="bg-gradient-to-r from-blue-900 to-blue-600 text-transparent bg-clip-text">
              TaxMantri
            </span>
            {/* Thick decorative underline behind the text */}
            <span className="absolute bottom-2 left-0 w-full h-8 bg-blue-200/50 -z-10 rounded-sm"></span>
          </h1>

          <p className="text-xl md:text-2xl text-gray-600 mb-8 max-w-2xl mx-auto font-medium">
            Tax smarter, Save better.
          </p>

          <button
            onClick={() => navigate('/input')}
            className="bg-[#1a1924] hover:bg-black text-white font-semibold text-lg px-8 py-4 rounded-full shadow-xl shadow-black/10 transition-transform active:scale-95"
          >
            Calculate my tax refund
          </button>
        </motion.div>
      </main>

      {/* Animated Purple Section */}
      <section className="px-4 md:px-8 pb-12" ref={scrollRef}>
        <motion.div
          style={{ scale: purpleScale }}
          className="bg-custom-purple rounded-3xl w-full max-w-7xl mx-auto overflow-hidden relative flex flex-col md:flex-row shadow-2xl"
        >
          {/* Subtle background graphic */}
          <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent pointer-events-none" />
          <svg className="absolute bottom-0 left-0 w-full h-full opacity-30 pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
            <path d="M0,100 C30,70 70,70 100,100" fill="white" />
          </svg>

          <div className="p-10 md:p-20 flex-1 flex flex-col justify-center z-10">
            <motion.h2
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="text-white text-5xl md:text-6xl font-extrabold leading-tight tracking-tight max-w-md"
            >
              It's just like having an accountant, in your pocket.
            </motion.h2>
          </div>

          <div className="flex-1 relative min-h-[400px] flex items-end justify-center pt-10">
            {/* Phone Mockup Graphic */}
            <motion.div
              initial={{ y: 100, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.7, type: "spring", stiffness: 100 }}
              className="w-72 bg-custom-dark rounded-t-3xl border-[8px] border-black shadow-2xl flex flex-col items-center relative z-10 overflow-hidden translate-y-2 lg:translate-y-8"
              style={{ height: '450px' }}
            >
              {/* Fake Phone Notch */}
              <div className="w-32 h-6 bg-black rounded-b-xl absolute top-0 z-20" />

              <div className="w-full p-6 pt-12 flex-1">
                <p className="text-gray-400 text-sm mb-1">2025/26</p>
                <h3 className="text-white text-2xl font-bold mb-8">Good afternoon, Rahul</h3>

                <div className="bg-[#2a2935] border border-gray-700/50 rounded-2xl p-5 shadow-lg">
                  <p className="text-gray-400 text-sm mb-2 flex justify-between items-center">
                    Real time tax
                    <span className="text-green-400">↑ 16%</span>
                  </p>
                  <p className="text-white text-3xl font-bold">₹43,500.67</p>
                  <div className="w-full h-1 bg-gray-700 mt-4 rounded-full overflow-hidden">
                    <div className="h-full bg-custom-purple w-2/3 rounded-full" />
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </motion.div>
      </section>

      {/* Feature Grids */}
      <section className="px-4 md:px-8 pb-24 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column Stack */}
          <div className="flex flex-col gap-6">
            {/* Dark Card */}
            <motion.div
              initial={{ y: 30, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.5 }}
              className="bg-custom-dark text-white rounded-3xl p-10 flex flex-col justify-between overflow-hidden relative min-h-[300px]"
            >
              <div className="z-10 relative">
                <h3 className="text-3xl font-bold mb-6 max-w-[250px] leading-tight">Personal tax management for retail</h3>
                <button
                  onClick={() => navigate('/how-it-works')}
                  className="flex items-center gap-2 text-sm font-semibold border border-white/20 rounded-full py-2 px-5 hover:bg-white/10 transition-colors"
                >
                  How it works <ArrowRight className="w-4 h-4" />
                </button>
              </div>
              {/* Graphic Illustration */}
              <div className="absolute right-0 bottom-0 w-48 h-48 pointer-events-none">
                <div className="w-full h-full flex flex-col items-center justify-end">
                  <div className="w-24 h-24 bg-[#5ce1ca] rounded-full translate-y-4" />
                  <div className="w-32 h-20 bg-custom-purple rounded-t-lg shadow-lg relative z-10 flex">
                    <div className="w-1/2 h-full bg-white ml-auto border-l-4 border-gray-200" />
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Green Card */}
            <motion.div
              onClick={() => navigate('/about')}
              initial={{ y: 30, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="bg-custom-green text-black rounded-3xl p-10 flex flex-col md:flex-row items-center overflow-hidden min-h-[300px] cursor-pointer hover:shadow-lg transition-transform hover:scale-[1.02]"
            >
              <div className="bg-white rounded-2xl p-6 shadow-xl relative w-full md:w-1/2 min-h-[200px] flex items-center justify-center gap-2 rotate-[-2deg]">
                <Code className="w-24 h-24 text-custom-purple" strokeWidth={1.5} />
              </div>
              <div className="mt-8 md:mt-0 md:ml-10 flex-1">
                <h3 className="text-4xl font-extrabold leading-tight text-black">About Us</h3>
              </div>
            </motion.div>
          </div>

          {/* Right Column / Image Card */}
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            whileInView={{ scale: 1, opacity: 1 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.6 }}
            className="rounded-3xl overflow-hidden relative flex flex-col justify-end min-h-[400px] lg:min-h-full group"
          >
            {/* Background Image Placeholder using Unsplash */}
            <div className="absolute inset-0 bg-gray-200">
              <img
                src={heroImage}
                alt="Professional at laptop"
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-1000"
              />
              {/* Dark gradient overlay so text is readable */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
            </div>

            <div className="p-10 relative z-10">
              <h3 className="text-white text-3xl font-bold mb-6 max-w-[300px] leading-snug">
                Thanks to TaxMantri, priya claimed back ₹1,00,600
              </h3>
              <button className="flex items-center gap-2 text-white text-sm font-semibold border border-white/30 rounded-full py-2 px-5 hover:bg-white/20 backdrop-blur-sm transition-colors w-fit">
                Check my refund <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-10 border-t border-gray-100 text-center text-gray-400 text-sm">
        <p>TaxMantri © {new Date().getFullYear()}. For educational purposes only. Consult a CA for filing advice.</p>
      </footer>
    </div>
  )
}
