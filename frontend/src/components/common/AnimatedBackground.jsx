import { motion } from 'framer-motion'

export default function AnimatedBackground() {
    return (
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
    )
}
