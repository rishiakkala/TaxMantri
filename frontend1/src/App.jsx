import { Routes, Route, Navigate } from 'react-router-dom'
import HeroPage from './pages/HeroPage.jsx'
import InputPage from './pages/InputPage.jsx'
import ResultsPage from './pages/ResultsPage.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HeroPage />} />
      <Route path="/input" element={<InputPage />} />
      <Route path="/results/:profileId" element={<ResultsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
