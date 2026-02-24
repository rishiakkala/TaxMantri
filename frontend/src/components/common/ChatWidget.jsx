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

/** Colour + label for confidence level */
const CONFIDENCE = {
    high: { color: 'bg-green-100 text-green-700', label: '● High confidence' },
    medium: { color: 'bg-yellow-100 text-yellow-700', label: '◐ Medium confidence' },
    low: { color: 'bg-red-100 text-red-600', label: '○ Low confidence' },
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
          ${isUser ? 'bg-gray-400' : 'bg-purple-600'}
        `}>
                    {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                </div>

                {/* Bubble */}
                <div className={`
          max-w-[75%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed
          ${isUser
                        ? 'bg-purple-600 text-white rounded-br-sm'
                        : 'bg-gray-50 border border-gray-100 text-gray-800 rounded-bl-sm'
                    }
        `}>
                    {msg.loading ? <TypingDots /> : msg.text}
                </div>
            </div>

            {/* Citation badges (AI only) */}
            {!isUser && msg.citations?.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-1.5 ml-9">
                    {msg.citations.map((c, i) => (
                        <span
                            key={i}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 text-xs font-bold border border-purple-200"
                        >
                            <BookOpen className="w-2.5 h-2.5" />
                            {c}
                        </span>
                    ))}
                </div>
            )}

            {/* Confidence badge (AI only, non-loading) */}
            {!isUser && !msg.loading && msg.confidence && (
                <div className="ml-9 mt-1">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CONFIDENCE[msg.confidence]?.color || ''}`}>
                        {CONFIDENCE[msg.confidence]?.label || msg.confidence}
                    </span>
                </div>
            )}
        </div>
    )
}

// ── Welcome message ───────────────────────────────────────────────────────────
const WELCOME = {
    id: '__welcome__',
    role: 'bot',
    text: "Hi! I'm your AI tax assistant powered by Mistral and India's Income Tax Act. Ask me anything — deductions, HRA, 80C limits, ITR-1 filing, or which regime suits you.",
    citations: [],
    confidence: null,
}

// Sample questions shown when chat is empty
const SAMPLE_QUESTIONS = [
    'What is the 80C investment limit?',
    'How is HRA exemption calculated?',
    'What is the new income tax slab for AY 2025-26?',
    'Is NPS eligible for deduction?',
]

// ── Main Widget ───────────────────────────────────────────────────────────────

/**
 * ChatWidget — mounts at app root, floats bottom-right on all pages.
 * Optional prop: profileId — if provided, answers are personalised.
 */
export default function ChatWidget({ profileId = null }) {
    const [open, setOpen] = useState(false)
    const [messages, setMessages] = useState([WELCOME])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const sessionId = useRef(getSessionId())
    const bottomRef = useRef(null)
    const inputRef = useRef(null)

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
                        confidence: data.confidence || 'low',
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
                        confidence: 'low',
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
                        <div className="flex items-center gap-3 px-4 py-3.5 bg-gradient-to-r from-purple-700 to-purple-500 text-white flex-shrink-0">
                            <div className="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center">
                                <Sparkles className="w-4.5 h-4.5" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="font-extrabold text-sm leading-tight">TaxMantri Assistant</p>
                                <p className="text-xs text-purple-200 font-medium">Powered by Mistral · Income Tax Act 1961</p>
                            </div>
                            <button
                                onClick={() => setOpen(false)}
                                className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center hover:bg-white/30 transition-colors"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Messages */}
                        <div className="flex-1 overflow-y-auto px-4 py-4 bg-white space-y-0">
                            {messages.map(msg => (
                                <MessageBubble key={msg.id} msg={msg} />
                            ))}
                            <div ref={bottomRef} />
                        </div>

                        {/* Sample questions — shown when only welcome msg exists */}
                        {messages.length === 1 && (
                            <div className="px-4 pb-2 flex flex-col gap-1.5 bg-white">
                                {SAMPLE_QUESTIONS.map((q, i) => (
                                    <button
                                        key={i}
                                        onClick={() => sendMessage(q)}
                                        className="text-left text-xs px-3 py-2 rounded-xl bg-purple-50 border border-purple-100 text-purple-700 font-semibold hover:bg-purple-100 transition-colors"
                                    >
                                        {q}
                                    </button>
                                ))}
                            </div>
                        )}

                        {/* Input bar */}
                        <form
                            onSubmit={handleSubmit}
                            className="flex items-center gap-2 px-3 py-3 bg-gray-50 border-t border-gray-100 flex-shrink-0"
                        >
                            <input
                                ref={inputRef}
                                type="text"
                                value={input}
                                onChange={e => setInput(e.target.value)}
                                placeholder="Ask a tax question…"
                                disabled={loading}
                                className="flex-1 text-sm px-3.5 py-2.5 rounded-2xl border border-gray-200 bg-white outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-100 transition-all disabled:opacity-50"
                            />
                            <button
                                type="submit"
                                disabled={!input.trim() || loading}
                                className="w-10 h-10 rounded-2xl bg-purple-600 flex items-center justify-center text-white hover:bg-purple-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
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
                className="fixed bottom-5 right-5 z-50 w-14 h-14 rounded-full bg-purple-600 text-white shadow-lg shadow-purple-300 flex items-center justify-center hover:bg-purple-700 transition-colors"
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
