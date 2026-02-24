import { useNavigate, useLocation } from 'react-router-dom';
import logoImage from '../images/justice_scales_black_gold.png';

export default function Navbar() {
    const navigate = useNavigate();
    const location = useLocation();

    // If we are on the home page, the translucent style works best with the hero background.
    // On other pages, we can use a slightly more opaque white to ensure readability.
    const isHome = location.pathname === '/';
    const navBgClass = isHome ? "bg-white/40 border-white/20" : "bg-white/80 border-gray-200 shadow-sm";

    return (
        <div className={`fixed top-0 left-0 w-full z-50 px-6 py-4 backdrop-blur-md border-b transition-all ${navBgClass}`}>
            <div className="max-w-7xl mx-auto flex items-center justify-between">
                <button onClick={() => navigate('/')} className="flex items-center gap-2 group">
                    <img src={logoImage} alt="TaxMantri Logo" className="h-9 w-auto object-contain group-hover:scale-105 transition-transform" />
                    <span style={{ fontFamily: "'Quicksand', sans-serif" }} className="font-extrabold text-2xl tracking-tighter text-black group-hover:text-custom-purple transition-colors">
                        TaxMantri
                    </span>
                </button>

                <nav className="hidden md:flex items-center gap-8 font-medium">
                    {!isHome && (
                        <button onClick={() => navigate('/')} className="text-gray-700 hover:text-black transition-colors">Home</button>
                    )}
                    <button onClick={() => navigate('/about')} className="text-gray-700 hover:text-black transition-colors">About Us</button>
                    <button onClick={() => navigate('/how-it-works')} className="text-gray-700 hover:text-black transition-colors">How it Works</button>
                    <button
                        onClick={() => navigate('/input')}
                        className="bg-black text-white px-5 py-2.5 rounded-full hover:bg-gray-800 transition-colors shadow-sm"
                    >
                        Get Started
                    </button>
                </nav>
            </div>
        </div>
    );
}
