import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import HeroPage from './pages/HeroPage.jsx'
import InputPage from './pages/InputPage.jsx'
import ResultsPage from './pages/ResultsPage.jsx'
import HowItWorksPage from './pages/HowItWorksPage.jsx'
import AboutPage from './pages/AboutPage.jsx'
import ChatWidget from './components/common/ChatWidget.jsx'
import AnimatedBackground from './components/common/AnimatedBackground.jsx'

function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return null
}

export default function App() {
  return (
    <>
      <AnimatedBackground />
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<HeroPage />} />
        <Route path="/how-it-works" element={<HowItWorksPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/input" element={<InputPage />} />
        <Route path="/results/:profileId" element={<ResultsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      {/* Floating RAG chatbot — available on every page */}
      <ChatWidget />
    </>
  )
}

