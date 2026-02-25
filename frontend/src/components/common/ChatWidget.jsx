/**
 * ChatWidget.jsx — Floating RAG-powered tax chatbot.
 *
 * Uses POST /api/query (MatcherAgent) which does:
 *   FAISS + BM25 hybrid retrieval → Mistral generation → Redis FAQ cache
 *
 * State is held here (lifted) so chat persists across page navigation.
 * session_id is persisted in localStorage for cross-reload history.
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    MessageCircle, X, Send, Bot, User,
    BookOpen, Loader2, ChevronDown, Sparkles,
} from 'lucide-react'
import { queryChat } from '../../api/endpoints.js'

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Returns or creates a stable UUID for this browser session */
function getSessionId() {
    let id = localStorage.getItem('taxmantri_chat_session')
    if (!id) {
        id = crypto.randomUUID()
        localStorage.setItem('taxmantri_chat_session', id)
    }
    return id
}

// ── Sub-components ────────────────────────────────────────────────────────────

function TypingDots() {
    return (
        <div className="flex items-center gap-1 py-1 px-1">
            {[0, 1, 2].map(i => (
                <span
                    key={i}
                    className="w-2 h-2 rounded-full bg-purple-400 animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                />
            ))}
        </div>
    )
}

function MessageBubble({ msg }) {
    const isUser = msg.role === 'user'

    return (
        <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} mb-3`}>
            {/* Avatar row */}
            <div className={`flex items-end gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
                {/* Avatar */}
                <div className={`
          w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-white text-xs
          ${isUser ? 'bg-[#7C3AED]' : 'bg-[#7C3AED]'}
        `}>
                    {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                </div>

                {/* Bubble */}
                <div className={`
          max-w-[75%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed
          ${isUser
                        ? 'bg-[#7C3AED] text-white rounded-br-sm shadow-sm'
                        : 'bg-purple-50 border border-purple-100 text-gray-800 rounded-bl-sm'
                    }
        `}>
                    {msg.loading ? <TypingDots /> : msg.text}
                </div>
            </div>

            {/* Citation badges (AI only) */}
            {!isUser && msg.citations?.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-1.5 ml-9">
                    {msg.citations.map((c, i) => {
                        // API returns {section, excerpt} objects — extract the section string
                        const label = typeof c === 'string' ? c : (c?.section || `Ref ${i + 1}`)
                        const tip = typeof c === 'object' ? (c?.excerpt || '') : ''
                        return (
                            <span
                                key={i}
                                title={tip}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 text-xs font-bold border border-purple-200"
                            >
                                <BookOpen className="w-2.5 h-2.5" />
                                {label}
                            </span>
                        )
                    })}
                </div>
            )}
        </div>
    )
}

// ── Welcome messages ─────────────────────────────────────────────────────────
const WELCOME_GENERIC = {
    id: '__welcome__',
    role: 'bot',
    text: "Hi! I'm your AI tax assistant powered by Mistral and India's Income Tax Act. Ask me anything — deductions, HRA, 80C limits, ITR-1 filing, or which regime suits you.",
    citations: [],
    confidence: null,
}

const WELCOME_PERSONALISED = {
    id: '__welcome__',
    role: 'bot',
    text: "Hi! I can see your tax analysis — I have your income details, deduction breakdown, and regime recommendation ready. Ask me anything about your results, how to save more tax, or any IT Act section.",
    citations: [],
    confidence: null,
}

// Sample questions — generic (no profile) vs personalised (with profile)
const SAMPLE_QUESTIONS_GENERIC = [
    'What is the 80C investment limit?',
    'How is HRA exemption calculated?',
    'What is the new income tax slab for AY 2025-26?',
    'Is NPS eligible for deduction?',
]

const SAMPLE_QUESTIONS_PERSONALISED = [
    'Why is my recommended regime better for me?',
    'How much tax can I save with more 80C investments?',
    'What deductions am I missing out on?',
    'Explain my taxable income calculation.',
]

// ── Main Widget ───────────────────────────────────────────────────────────────

/**
 * ChatWidget — mounts at app root, floats bottom-right on all pages.
 * Optional prop: profileId — if provided, answers are personalised.
 */
export default function ChatWidget({ profileId: propProfileId = null }) {
    const [open, setOpen] = useState(false)
    // Lazy initializer: pick the correct welcome message at mount time based on
    // whether a profile is already stored. Avoids referencing the local `WELCOME`
    // variable before profileId has been computed.
    const [messages, setMessages] = useState(() => {
        const hasProfile = propProfileId || !!localStorage.getItem('taxmantri_profile_id')
        return [hasProfile ? WELCOME_PERSONALISED : WELCOME_GENERIC]
    })
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const sessionId = useRef(getSessionId())
    const bottomRef = useRef(null)
    const inputRef = useRef(null)

    // Use prop if given, otherwise read the profileId the ResultsPage saved to localStorage.
    // This lets the backend personalise answers with the user's own salary/deductions/regime.
    const profileId = propProfileId || localStorage.getItem('taxmantri_profile_id')

    // Pick welcome message and sample questions based on whether we have a profile
    const SAMPLE_QUESTIONS = profileId ? SAMPLE_QUESTIONS_PERSONALISED : SAMPLE_QUESTIONS_GENERIC

    // Auto-scroll to bottom on new message
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    // Focus input when widget opens
    useEffect(() => {
        if (open) setTimeout(() => inputRef.current?.focus(), 200)
    }, [open])

    const sendMessage = useCallback(async (question) => {
        if (!question.trim() || loading) return

        const userMsg = { id: Date.now(), role: 'user', text: question }
        const botPlaceholder = { id: Date.now() + 1, role: 'bot', text: '', loading: true }

        setMessages(prev => [...prev, userMsg, botPlaceholder])
        setInput('')
        setLoading(true)

        try {
            const data = await queryChat(question, sessionId.current, profileId)
            setMessages(prev => prev.map(m =>
                m.id === botPlaceholder.id
                    ? {
                        ...m,
                        loading: false,
                        text: data.answer || 'No answer returned.',
                        citations: data.citations || [],
                    }
                    : m
            ))
        } catch (err) {
            const isUnavailable = err?.response?.status === 503
            setMessages(prev => prev.map(m =>
                m.id === botPlaceholder.id
                    ? {
                        ...m,
                        loading: false,
                        text: isUnavailable
                            ? 'The knowledge base is still loading. Please try again in a moment.'
                            : 'Something went wrong. Please try again.',
                        citations: [],
                    }
                    : m
            ))
        } finally {
            setLoading(false)
        }
    }, [loading, profileId])

    const handleSubmit = (e) => {
        e.preventDefault()
        sendMessage(input)
    }

    const unreadCount = messages.filter(m => m.role === 'bot' && m.id !== '__welcome__').length

    return (
        <>
            {/* ── Chat Panel ──────────────────────────────────────────────── */}
            <AnimatePresence>
                {open && (
                    <motion.div
                        key="chat-panel"
                        initial={{ opacity: 0, y: 20, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 20, scale: 0.95 }}
                        transition={{ duration: 0.22, ease: 'easeOut' }}
                        className="fixed bottom-24 right-5 z-50 w-[360px] max-h-[560px] flex flex-col rounded-3xl shadow-2xl border border-purple-100 bg-white overflow-hidden"
                        style={{ boxShadow: '0 24px 60px rgba(124,58,237,0.18)' }}
                    >
                        {/* Header */}
                        <div className="flex items-center gap-3 px-4 py-3.5 bg-white border-b border-purple-100 text-gray-900 flex-shrink-0">
                            <div className="w-9 h-9 rounded-xl bg-[#7C3AED] flex items-center justify-center text-white">
                                <Sparkles className="w-4.5 h-4.5" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="font-extrabold text-sm leading-tight text-gray-900">TaxMantri Assistant</p>
                            </div>
                            <button
                                onClick={() => setOpen(false)}
                                className="w-7 h-7 rounded-full bg-purple-50 flex items-center justify-center hover:bg-purple-100 transition-colors"
                            >
                                <X className="w-4 h-4 text-purple-600" />
                            </button>
                        </div>

                        {/* Messages */}
                        <div className="flex-1 overflow-y-auto px-4 py-4 bg-purple-50/50 space-y-0">
                            {messages.map(msg => (
                                <MessageBubble key={msg.id} msg={msg} />
                            ))}
                            <div ref={bottomRef} />
                        </div>

                        {/* Sample questions — shown when only welcome msg exists */}
                        {messages.length === 1 && (
                            <div className="px-4 pb-2 flex flex-col gap-1.5 bg-transparent">
                                {SAMPLE_QUESTIONS.map((q, i) => (
                                    <button
                                        key={i}
                                        onClick={() => sendMessage(q)}
                                        className="text-left text-xs px-3 py-2 rounded-xl bg-white border border-purple-200 text-purple-700 font-semibold hover:bg-purple-50 transition-colors shadow-sm"
                                    >
                                        {q}
                                    </button>
                                ))}
                            </div>
                        )}

                        {/* Input bar */}
                        <form
                            onSubmit={handleSubmit}
                            className="flex items-center gap-2 px-3 py-3 bg-white border-t border-purple-100 flex-shrink-0"
                        >
                            <input
                                ref={inputRef}
                                type="text"
                                value={input}
                                onChange={e => setInput(e.target.value)}
                                placeholder="Ask a tax question…"
                                disabled={loading}
                                className="flex-1 text-sm px-3.5 py-2.5 rounded-2xl border border-purple-200 bg-purple-50 text-gray-800 placeholder-purple-300 outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-200 transition-all disabled:opacity-50"
                            />
                            <button
                                type="submit"
                                disabled={!input.trim() || loading}
                                className="w-10 h-10 rounded-2xl bg-[#7C3AED] flex items-center justify-center text-white hover:bg-purple-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0 shadow-md"
                            >
                                {loading
                                    ? <Loader2 className="w-4 h-4 animate-spin" />
                                    : <Send className="w-4 h-4" />
                                }
                            </button>
                        </form>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── Floating Button ──────────────────────────────────────────── */}
            <motion.button
                onClick={() => setOpen(v => !v)}
                whileHover={{ scale: 1.08 }}
                whileTap={{ scale: 0.95 }}
                className="fixed bottom-5 right-5 z-50 w-14 h-14 rounded-full bg-[#7C3AED] text-white shadow-[0_4px_20px_rgba(124,58,237,0.45)] flex items-center justify-center hover:bg-purple-700 hover:shadow-[0_8px_28px_rgba(124,58,237,0.55)] transition-all duration-300"
                aria-label="Open tax chatbot"
            >
                <AnimatePresence mode="wait">
                    {open
                        ? <motion.span key="down" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                            <ChevronDown className="w-6 h-6" />
                        </motion.span>
                        : <motion.span key="chat" initial={{ rotate: 90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                            <MessageCircle className="w-6 h-6" />
                        </motion.span>
                    }
                </AnimatePresence>

                {/* Unread dot — shows when widget is closed and there are AI replies */}
                {!open && unreadCount > 0 && (
                    <span className="absolute top-1 right-1 w-3.5 h-3.5 rounded-full bg-red-500 border-2 border-white" />
                )}
            </motion.button>
        </>
    )
}
