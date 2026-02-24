import client from './client.js'

/**
 * Upload a Form 16 PDF/image for OCR extraction.
 * Returns { session_id, extracted_fields, summary, warnings }
 */
export async function uploadForm16(file) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await client.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000, // OCR can take longer
  })
  return response.data
}

/**
 * Confirm OCR-extracted profile with user edits.
 * body: { session_id, edited_fields }
 * Returns { profile_id, status: 'confirmed' }
 */
export async function confirmProfile(body) {
  const response = await client.put('/profile/confirm', body)
  return response.data
}

/**
 * Create a profile from manual wizard entry.
 * body: Full UserFinancialProfile JSON
 * Returns { profile_id, session_id, status, validation_errors }
 */
export async function createProfile(body) {
  const response = await client.post('/profile', body)
  return response.data
}

/**
 * Calculate tax for a stored profile.
 * body: { profile_id }
 * Returns full TaxResult JSON
 */
export async function calculateTax(profileId) {
  const response = await client.post('/calculate', { profile_id: profileId })
  return response.data
}

/**
 * Get ITR-1 field mapping for a profile.
 * Returns array of { itr1_field, schedule, value, source_field, regime, note }
 */
export async function getITR1Mapping(profileId) {
  const response = await client.get(`/itr1-mapping/${profileId}`)
  return response.data
}

/**
 * Download the tax report PDF for a profile.
 * Returns a Blob for browser download.
 */
export async function exportPDF(profileId) {
  const response = await client.get(`/export/${profileId}`, {
    responseType: 'blob',
  })
  return response.data
}

/**
 * Ask a tax question — RAG retrieval + Mistral answer with IT Act citations.
 * question:   plain-English tax query
 * sessionId:  UUID for chat history tracking (persisted in localStorage)
 * profileId:  optional — personalises answer using user's financial profile
 *
 * Returns { answer, confidence, citations, cached }
 */
export async function queryChat(question, sessionId, profileId = null) {
  const body = { question, session_id: sessionId }
  if (profileId) body.profile_id = profileId
  const response = await client.post('/query', body)
  return response.data
}

/**
 * Fetch full Q&A chat history for a session from PostgreSQL.
 * Returns { session_id, messages: [{question, answer, confidence, created_at}] }
 */
export async function getChatHistory(sessionId) {
  const response = await client.get(`/chat/history`, { params: { session_id: sessionId } })
  return response.data
}

