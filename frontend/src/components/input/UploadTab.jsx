import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { uploadForm16, confirmProfile, calculateTax } from '../../api/endpoints.js'
import OCRFieldReview from './OCRFieldReview.jsx'
import ErrorBanner from '../common/ErrorBanner.jsx'

const REQUIRED_EXTRA_FIELDS = ['monthly_rent_paid', 'city_type', 'age_bracket']

/**
 * Props:
 *   onCalculationComplete (fn) — called with (profileId, taxResult) after full flow
 *   onCalculating (fn)         — called with bool to show/hide loading overlay
 */
export default function UploadTab({ onCalculationComplete, onCalculating }) {
  const [phase, setPhase] = useState('idle') // idle | uploading | review | confirming
  const [sessionId, setSessionId] = useState(null)
  const [extractedFields, setExtractedFields] = useState({})
  const [ocrSummary, setOcrSummary] = useState(null)
  const [fieldEdits, setFieldEdits] = useState({})
  const [extraFields, setExtraFields] = useState({
    monthly_rent_paid: '',
    city_type: 'metro',
    age_bracket: 'under60',
    parent_senior_citizen: false,
  })
  const [error, setError] = useState(null)

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0]
    if (!file) return

    setError(null)
    setPhase('uploading')

    try {
      const result = await uploadForm16(file)
      setSessionId(result.session_id)
      setExtractedFields(result.extracted_fields ?? {})
      setOcrSummary(result.summary)
      setPhase('review')
      toast.success(`Extracted ${result.summary?.green_count ?? 0} fields automatically.`)
    } catch (err) {
      setPhase('idle')
      setError(err?.response?.data ?? 'OCR extraction failed. Please try again.')
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
    },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
    onDropRejected: (files) => {
      const err = files[0]?.errors?.[0]
      if (err?.code === 'file-too-large') toast.error('File exceeds 10 MB limit.')
      else if (err?.code === 'file-invalid-type') toast.error('Only PDF, JPEG, PNG allowed.')
      else toast.error('Invalid file.')
    },
  })

  const handleConfirm = async () => {
    // Validate extra fields
    if (!extraFields.city_type) {
      toast.error('Please select your city type.')
      return
    }
    if (!extraFields.age_bracket) {
      toast.error('Please select your age bracket.')
      return
    }

    setError(null)
    setPhase('confirming')
    onCalculating?.(true)

    try {
      // Merge OCR edits with extra fields
      const editedFields = {
        ...fieldEdits,
        monthly_rent_paid: Number(extraFields.monthly_rent_paid) || 0,
        city_type: extraFields.city_type,
        age_bracket: extraFields.age_bracket,
        parent_senior_citizen: extraFields.parent_senior_citizen,
        input_method: 'ocr',
      }

      const confirmResult = await confirmProfile({ session_id: sessionId, edited_fields: editedFields })
      const profileId = confirmResult.profile_id

      const taxResult = await calculateTax(profileId)
      onCalculatingComplete(profileId, taxResult)
    } catch (err) {
      setPhase('review')
      onCalculating?.(false)
      setError(err?.response?.data ?? 'Confirmation failed. Please try again.')
    }
  }

  const onCalculatingComplete = (profileId, taxResult) => {
    onCalculationComplete?.(profileId, taxResult)
  }

  return (
    <div>
      <ErrorBanner error={error} onDismiss={() => setError(null)} />

      <AnimatePresence mode="wait">
        {phase === 'idle' || phase === 'uploading' ? (
          <motion.div
            key="dropzone"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div
              {...getRootProps()}
              className={[
                'border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-colors',
                isDragActive
                  ? 'border-navy bg-navy/5'
                  : 'border-gray-300 hover:border-navy/60 hover:bg-gray-50',
                phase === 'uploading' ? 'pointer-events-none opacity-60' : '',
              ].join(' ')}
            >
              <input {...getInputProps()} />
              {phase === 'uploading' ? (
                <div className="flex flex-col items-center gap-3">
                  <div className="w-12 h-12 border-4 border-navy/20 border-t-navy rounded-full animate-spin" />
                  <p className="text-navy font-medium">Uploading & extracting…</p>
                  <p className="text-gray-500 text-sm">This may take 10–30 seconds</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <div className="w-14 h-14 rounded-2xl bg-navy/10 flex items-center justify-center">
                    {isDragActive ? (
                      <FileText className="w-7 h-7 text-navy" />
                    ) : (
                      <Upload className="w-7 h-7 text-navy/60" />
                    )}
                  </div>
                  <div>
                    <p className="text-navy font-semibold text-lg">
                      {isDragActive ? 'Drop it here!' : 'Upload Form 16'}
                    </p>
                    <p className="text-gray-500 text-sm mt-1">
                      Drag & drop or click to browse · PDF, JPEG, PNG · Max 10 MB
                    </p>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="review"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {/* Summary chips */}
            {ocrSummary && (
              <div className="flex gap-2 flex-wrap mb-4">
                {ocrSummary.green_count > 0 && (
                  <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-success-light text-success font-medium border border-success/30">
                    <CheckCircle className="w-3.5 h-3.5" />
                    {ocrSummary.green_count} auto-filled
                  </span>
                )}
                {ocrSummary.yellow_count > 0 && (
                  <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-amber-50 text-amber font-medium border border-amber/30">
                    <AlertCircle className="w-3.5 h-3.5" />
                    {ocrSummary.yellow_count} to review
                  </span>
                )}
                {ocrSummary.red_count > 0 && (
                  <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-red-50 text-red-600 font-medium border border-red-200">
                    {ocrSummary.red_count} not extracted
                  </span>
                )}
              </div>
            )}

            {/* OCR field review */}
            <OCRFieldReview
              extractedFields={extractedFields}
              onChange={(edits) => setFieldEdits(edits)}
            />

            {/* Extra fields not in Form 16 */}
            <div className="mt-6 border-t pt-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">
                Additional details (not on Form 16)
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-700 mb-1 block">
                    Monthly Rent Paid (₹)
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">₹</span>
                    <input
                      type="number"
                      min={0}
                      value={extraFields.monthly_rent_paid}
                      onChange={(e) => setExtraFields(prev => ({ ...prev, monthly_rent_paid: e.target.value }))}
                      className="w-full pl-7 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy/30 focus:border-navy"
                      placeholder="0"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-700 mb-1 block">City Type <span className="text-red-500">*</span></label>
                  <select
                    value={extraFields.city_type}
                    onChange={(e) => setExtraFields(prev => ({ ...prev, city_type: e.target.value }))}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy/30 focus:border-navy"
                  >
                    <option value="metro">Metro (Mumbai, Delhi, Chennai, Kolkata)</option>
                    <option value="non_metro">Non-Metro</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-700 mb-1 block">Age Bracket <span className="text-red-500">*</span></label>
                  <select
                    value={extraFields.age_bracket}
                    onChange={(e) => setExtraFields(prev => ({ ...prev, age_bracket: e.target.value }))}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy/30 focus:border-navy"
                  >
                    <option value="under60">Under 60</option>
                    <option value="60_79">60–79 (Senior Citizen)</option>
                    <option value="80plus">80+ (Super Senior Citizen)</option>
                  </select>
                </div>
                <div className="flex items-center gap-2 pt-5">
                  <input
                    type="checkbox"
                    id="parent_sc"
                    checked={extraFields.parent_senior_citizen}
                    onChange={(e) => setExtraFields(prev => ({ ...prev, parent_senior_citizen: e.target.checked }))}
                    className="w-4 h-4 rounded border-gray-300 text-navy focus:ring-navy/30"
                  />
                  <label htmlFor="parent_sc" className="text-sm text-gray-700">
                    Parents are senior citizens (60+)
                  </label>
                </div>
              </div>
            </div>

            <div className="mt-6 flex gap-3">
              <button
                onClick={() => { setPhase('idle'); setExtractedFields({}); setSessionId(null) }}
                className="px-4 py-2.5 text-sm bg-black/60 text-white backdrop-blur-md border border-white/20 rounded-xl hover:bg-black/80 transition-colors"
              >
                Re-upload
              </button>
              <button
                onClick={handleConfirm}
                disabled={phase === 'confirming'}
                className="flex-1 px-6 py-2.5 bg-black/60 backdrop-blur-md border border-white/20 text-white font-semibold text-sm rounded-xl shadow-[0_4px_16px_rgba(0,0,0,0.2)] hover:bg-black/80 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(0,0,0,0.3)] transition-all duration-300 active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:translate-y-0"
              >
                {phase === 'confirming' ? 'Confirming…' : 'Confirm & Analyse Tax'}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
