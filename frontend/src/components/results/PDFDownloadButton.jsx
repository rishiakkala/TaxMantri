import { useState } from 'react'
import { Download, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { exportPDF } from '../../api/endpoints.js'

/**
 * Props:
 *   profileId (string)
 */
export default function PDFDownloadButton({ profileId }) {
  const [loading, setLoading] = useState(false)

  const handleDownload = async () => {
    if (!profileId || loading) return

    setLoading(true)
    try {
      const blob = await exportPDF(profileId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `TaxMantri_AY2025-26_${profileId.slice(0, 8)}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success('PDF downloaded!')
    } catch {
      toast.error('PDF generation failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={handleDownload}
      disabled={loading || !profileId}
      className={[
        'inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold',
        'border-2 border-navy text-navy hover:bg-navy hover:text-white',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'transition-all duration-200',
      ].join(' ')}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <Download className="w-4 h-4" />
      )}
      {loading ? 'Generating PDF…' : 'Download PDF Report'}
    </button>
  )
}
