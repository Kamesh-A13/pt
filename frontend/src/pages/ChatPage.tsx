import React, { useState, useEffect, useRef } from 'react'
import {
  Send,
  Bot,
  User,
  FileText,
  BookOpen,
  Sparkles,
  AlertCircle,
  Loader2,
  Trash2,
  ExternalLink,
} from 'lucide-react'
import { sendChatMessage, listDocuments } from '../api/apiService'
import type { ChatResponse, DocumentItem } from '../types'

const SUBJECTS = [
  'Python Programming',
  'Java & OOP',
  'Data Structures & Algorithms',
  'Computer Networks',
  'Artificial Intelligence',
  'Machine Learning',
  'Operating Systems',
  'Mathematics & Calculus',
]

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ source: string; page: number; score: number }>
}

export const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        '👋 Welcome to StudyOS AI Chat! You can ask questions about your uploaded lecture documents, or select an academic subject for general study assistance.',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<'short' | 'medium' | 'detailed'>('medium')
  const [chatType, setChatType] = useState<'document' | 'general'>('document')
  const [selectedDocId, setSelectedDocId] = useState<string>('')
  const [selectedSubject, setSelectedSubject] = useState<string>(SUBJECTS[0])
  const [documents, setDocuments] = useState<DocumentItem[]>([])

  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    listDocuments()
      .then((docs) => {
        setDocuments(docs)
        if (docs.length > 0 && !selectedDocId) {
          setSelectedDocId(docs[0].doc_id)
        }
      })
      .catch((err) => console.error('Error loading documents:', err))
  }, [selectedDocId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async (e?: React.FormEvent, overrideText?: string) => {
    if (e) e.preventDefault()
    const userText = (overrideText ?? input).trim()
    if (!userText || loading) return

    setInput('')
    setError(null)

    const newHistory = [...messages, { role: 'user' as const, content: userText }]
    setMessages(newHistory)
    setLoading(true)

    try {
      const historyPayload = newHistory
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }))

      const response: ChatResponse = await sendChatMessage({
        doc_id: chatType === 'document' ? selectedDocId || null : null,
        subject: chatType === 'general' ? selectedSubject : null,
        message: userText,
        history: historyPayload,
        mode,
      })

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.response,
          sources: response.sources,
        },
      ])
    } catch (err: any) {
      console.error(err)
      setError(
        err.response?.data?.detail ||
          'Failed to communicate with Ollama. Make sure Ollama is running (`ollama serve`) and the model is pulled.'
      )
    } finally {
      setLoading(false)
    }
  }

  const handleClearChat = () => {
    setMessages([
      {
        role: 'assistant',
        content: 'Chat cleared. How can I help you study today?',
      },
    ])
    setError(null)
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 flex items-center gap-2.5">
            <Bot className="w-8 h-8 text-blue-600" />
            AI Study Chat
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Grounded RAG answers from lecture materials and academic tutoring powered by local Ollama.
          </p>
        </div>

        <button
          onClick={handleClearChat}
          className="self-start md:self-auto flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-xs"
        >
          <Trash2 className="w-3.5 h-3.5 text-slate-400" />
          Clear Conversation
        </button>
      </div>

      {/* Control Bar: Mode, Target & Subject */}
      <div className="glass-card p-4 mb-6 flex flex-wrap items-center justify-between gap-4">
        {/* Toggle Document vs General */}
        <div className="flex items-center p-1 bg-slate-100 rounded-xl text-xs font-bold">
          <button
            onClick={() => setChatType('document')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
              chatType === 'document' ? 'bg-white text-blue-700 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Document RAG
          </button>
          <button
            onClick={() => setChatType('general')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
              chatType === 'general' ? 'bg-white text-blue-700 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            Subject Tutoring
          </button>
        </div>

        {/* Document Selector or Subject Selector */}
        {chatType === 'document' ? (
          <div className="flex items-center gap-2 flex-1 min-w-[200px]">
            <span className="text-xs font-semibold text-slate-500 whitespace-nowrap">Document:</span>
            {documents.length > 0 ? (
              <select
                value={selectedDocId}
                onChange={(e) => setSelectedDocId(e.target.value)}
                className="w-full text-xs font-medium border border-slate-300 rounded-lg p-2 bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
              >
                {documents.map((d) => (
                  <option key={d.doc_id} value={d.doc_id}>
                    {d.filename} ({d.word_count} words)
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-xs text-amber-600 font-medium">
                No documents uploaded yet. Go to "PDF Notes" to upload.
              </span>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-2 flex-1 min-w-[200px]">
            <span className="text-xs font-semibold text-slate-500 whitespace-nowrap">Subject:</span>
            <select
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value)}
              className="w-full text-xs font-medium border border-slate-300 rounded-lg p-2 bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
            >
              {SUBJECTS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Answer Mode Selector */}
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-600">
          <span className="text-slate-500">Mode:</span>
          {(['short', 'medium', 'detailed'] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`capitalize px-2.5 py-1 rounded-md text-xs transition-colors ${
                mode === m
                  ? 'bg-blue-600 text-white font-bold'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Ollama Communication Error</p>
            <p className="text-xs mt-0.5 text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Chat Messages Log */}
      <div className="glass-card min-h-[480px] max-h-[600px] flex flex-col justify-between overflow-hidden">
        <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-4">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex items-start gap-3 ${
                m.role === 'user' ? 'flex-row-reverse' : 'flex-row'
              }`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-white shadow-xs ${
                  m.role === 'user'
                    ? 'bg-blue-600'
                    : 'bg-gradient-to-tr from-indigo-600 to-blue-500'
                }`}
              >
                {m.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Message Bubble */}
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-xs ${
                  m.role === 'user'
                    ? 'bg-blue-600 text-white font-medium rounded-tr-xs'
                    : 'bg-white border border-slate-200 text-slate-800 rounded-tl-xs'
                }`}
              >
                <div className="whitespace-pre-wrap">{m.content}</div>

                {/* Grounding Source Attribution Badges */}
                {m.sources && m.sources.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-slate-100">
                    <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1 mb-1.5">
                      <Sparkles className="w-3 h-3 text-blue-500" />
                      Retrieved Sources & Context Citations:
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {m.sources.map((s, sidx) => (
                        <span
                          key={sidx}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-[11px] font-semibold border border-blue-100"
                        >
                          <FileText className="w-3 h-3" />
                          {s.source} {s.page >= 0 ? `(p. ${s.page})` : ''} • Match: {(s.score * 100).toFixed(0)}%
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 to-blue-500 flex items-center justify-center text-white shrink-0">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-white border border-slate-200 text-slate-600 text-sm rounded-2xl rounded-tl-xs px-4 py-3 flex items-center gap-2">
                <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                <span>Ollama is thinking and retrieving context...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Suggested Conversation Starters */}
        <div className="px-3 sm:px-4 py-2.5 bg-slate-100/80 border-t border-slate-200 flex items-center gap-2 overflow-x-auto text-xs">
          <span className="text-slate-400 font-bold shrink-0 text-[11px] uppercase tracking-wider">Try:</span>
          {[
            { label: '👋 Hi!', prompt: 'Hi!' },
            { label: '⏱️ How much time will it take?', prompt: 'How much time will it take to complete?' },
            { label: '💡 How to study it simple?', prompt: 'How to study it simple?' },
            { label: '📝 Key takeaways', prompt: 'What are the main key takeaways and core concepts?' },
            { label: '👶 Explain simply (ELI5)', prompt: 'Explain the core concept in very simple terms' },
          ].map((chip, idx) => (
            <button
              key={idx}
              type="button"
              disabled={loading}
              onClick={() => handleSend(undefined, chip.prompt)}
              className="shrink-0 px-2.5 py-1 rounded-full bg-white hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 hover:border-blue-300 font-medium transition-colors shadow-2xs disabled:opacity-50 cursor-pointer"
            >
              {chip.label}
            </button>
          ))}
        </div>

        {/* Chat Input Bar */}
        <form onSubmit={handleSend} className="p-3 sm:p-4 bg-slate-50 border-t border-slate-200 flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              chatType === 'document'
                ? selectedDocId
                  ? 'Ask anything from your document (e.g. explain backpropagation)...'
                  : 'Upload a document first to query...'
                : `Ask any question about ${selectedSubject}...`
            }
            className="flex-1 text-sm bg-white border border-slate-300 rounded-xl px-4 py-3 focus:outline-hidden focus:ring-2 focus:ring-blue-500 shadow-inner"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold flex items-center gap-1.5 transition-colors shadow-md shadow-blue-500/20"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            <span className="hidden sm:inline">Send</span>
          </button>
        </form>
      </div>
    </div>
  )
}
export default ChatPage
