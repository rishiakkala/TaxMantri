import { useState } from 'react'
import { ChevronDown, Loader2 } from 'lucide-react'
import { getITR1Mapping } from '../../api/endpoints.js'

const INR = (v) => '₹' + Number(v ?? 0).toLocaleString('en-IN')

/**
 * Lazy-fetch collapsible ITR-1 field mapping table.
 *
 * Props:
 *   profileId (string)
 */
export default function ITR1Table({ profileId }) {
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [mapping, setMapping] = useState(null)
  const [error, setError] = useState(null)

  const handleToggle = async () => {
    if (!expanded && !mapping && !loading) {
      // First open — fetch data
      setLoading(true)
      setError(null)
      try {
        const data = await getITR1Mapping(profileId)
        setMapping(data)
      } catch {
        setError('Could not load ITR-1 mapping.')
      } finally {
        setLoading(false)
      }
    }
    setExpanded((prev) => !prev)
  }

  const oldEntries = mapping?.filter((e) => e.regime === 'old') ?? []
  const newEntries = mapping?.filter((e) => e.regime === 'new') ?? []
  const commonEntries = mapping?.filter((e) => !e.regime || e.regime === 'both') ?? []

  return (
    <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
      {/* Toggle header */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors"
      >
        <div className="text-left">
          <h3 className="font-semibold text-navy">ITR-1 Sahaj Field Mapping</h3>
          <p className="text-gray-500 text-xs mt-0.5">
            See how your numbers map to ITR-1 form fields
          </p>
        </div>
        <div className="flex items-center gap-2">
          {loading && <Loader2 className="w-4 h-4 animate-spin text-navy" />}
          <ChevronDown
            className={[
              'w-5 h-5 text-gray-400 transition-transform',
              expanded ? 'rotate-180' : '',
            ].join(' ')}
          />
        </div>
      </button>

      {/* Content */}
      {expanded && (
        <div className="border-t border-gray-200 p-5">
          {error ? (
            <p className="text-red-600 text-sm text-center py-4">{error}</p>
          ) : loading ? (
            <div className="flex items-center justify-center py-8 gap-2 text-gray-500">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">Loading field mapping…</span>
            </div>
          ) : mapping ? (
            <div className="space-y-5">
              {[
                { label: 'Common Fields (Both Regimes)', entries: commonEntries },
                { label: 'Old Regime Fields', entries: oldEntries },
                { label: 'New Regime Fields', entries: newEntries },
              ].map(({ label, entries }) => {
                if (entries.length === 0) return null
                return (
                  <div key={label}>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                      {label}
                    </h4>
                    <div className="rounded-xl border border-gray-200 overflow-hidden">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="bg-gray-50 border-b border-gray-200">
                            <th className="text-left px-4 py-2 text-xs font-semibold text-gray-600">ITR-1 Field</th>
                            <th className="text-left px-4 py-2 text-xs font-semibold text-gray-600">Schedule</th>
                            <th className="text-right px-4 py-2 text-xs font-semibold text-gray-600">Amount</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {entries.map((entry, i) => (
                            <tr key={i} className="hover:bg-gray-50">
                              <td className="px-4 py-2.5 text-gray-800">{entry.itr1_field}</td>
                              <td className="px-4 py-2.5 text-gray-500 text-xs">{entry.schedule}</td>
                              <td className="px-4 py-2.5 text-right font-medium text-navy">
                                {INR(entry.value)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {entries.some((e) => e.note) && (
                      <div className="mt-2 space-y-1">
                        {entries.filter((e) => e.note).map((e, i) => (
                          <p key={i} className="text-xs text-gray-500 italic">
                            * {e.itr1_field}: {e.note}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}
