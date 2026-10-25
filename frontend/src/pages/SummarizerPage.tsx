import React, { useState, useEffect } from 'react'
import {
  FileCode,
  Sparkles,
  Copy,
  Check,
  Loader2,
  AlertCircle,
  FileText,
  Bookmark,
} from 'lucide-react'
import { getSummary, listDocuments } from '../api/apiService'
import type { DocumentItem } from '../types'

const MODES = [
  { id: 'short', label: 'Short Summary', desc: 'Brief overview under 3 paragraphs' },
  { id: 'medium', label: 'Medium Summary', desc: 'Balanced coverage of core ideas' },
  { id: 'detailed', label: 'Detailed Summary', desc: 'Exhaustive topic-by-topic analysis' },
  { id: 'key_points', label: 'Key Points', desc: 'Numbered list of critical takeaways' },
  { id: 'definitions', label: 'Definitions Glossary', desc: 'Core terms and exact definitions' },
  { id: 'important_terms', label: 'Important Terms', desc: 'Domain keywords with 1-line explanations' },
  { id: 'exam_revision', label: 'Exam Revision Notes', desc: 'High-yield cheat-sheet for exams' },
]

export const SummarizerPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [selectedDocId, setSelectedDocId] = useState<string>('')
  const [customTopic, setCustomTopic] = useState<string>('')
  const [sourceType, setSourceType] = useState<'document' | 'topic'>('document')
  const [mode, setMode] = useState<string>('medium')
  const [difficulty, setDifficulty] = useState<string>('Intermediate')
  const [loading, setLoading] = useState(false)
  const [summary, setSummary] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    listDocuments()
      .then((docs) => {
        setDocuments(docs)
        if (docs.length > 0 && !selectedDocId) {
          setSelectedDocId(docs[0].doc_id)
        }
      })
      .catch((err) => console.error(err))
  }, [selectedDocId])

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSummary(null)
    setLoading(true)

    try {
      const res = await getSummary({
        doc_id: sourceType === 'document' ? selectedDocId || undefined : undefined,
        topic: sourceType === 'topic' ? customTopic || undefined : undefined,
        difficulty,
        mode,
      })
      setSummary(res.summary)
    } catch (err: any) {
      console.error(err)
      setError(
        err.response?.data?.detail ||
          'Failed to generate summary with Ollama. Make sure Ollama is running and model llama3.2 is available.'
      )
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = () => {
    if (!summary) return
    navigator.clipboard.writeText(summary)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Title */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 flex items-center gap-2.5">
          <FileCode className="w-8 h-8 text-blue-600" />
          Notes Summarizer & Revision Generator
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          Transform heavy study materials into structured revision summaries, glossaries, key points, and exam cheat-sheets.
        </p>
      </div>

      {/* Grid: Form and Output */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Configuration Form */}
        <div className="lg:col-span-5 space-y-5">
          <form onSubmit={handleGenerate} className="glass-card p-6 space-y-5">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-600" />
              Summarization Settings
            </h2>

            {/* Source Type Toggle */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Source Material
              </label>
              <div className="flex items-center p-1 bg-slate-100 rounded-xl text-xs font-bold">
                <button
                  type="button"
                  onClick={() => setSourceType('document')}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg transition-all ${
                    sourceType === 'document' ? 'bg-white text-blue-700 shadow-xs' : 'text-slate-600'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  Uploaded Document
                </button>
                <button
                  type="button"
                  onClick={() => setSourceType('topic')}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg transition-all ${
                    sourceType === 'topic' ? 'bg-white text-blue-700 shadow-xs' : 'text-slate-600'
                  }`}
                >
                  <Bookmark className="w-3.5 h-3.5" />
                  Custom Topic
                </button>
              </div>
            </div>

            {sourceType === 'document' ? (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">Select Document</label>
                {documents.length > 0 ? (
                  <select
                    value={selectedDocId}
                    onChange={(e) => setSelectedDocId(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-xl p-2.5 bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                  >
                    {documents.map((d) => (
                      <option key={d.doc_id} value={d.doc_id}>
                        {d.filename} ({d.word_count} words)
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="p-3 bg-amber-50 rounded-xl text-xs text-amber-800 border border-amber-200">
                    No documents found. Switch to "Custom Topic" or upload a document in "PDF Notes".
                  </div>
                )}
              </div>
            ) : (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">Topic or Subject</label>
                <input
                  type="text"
                  value={customTopic}
                  onChange={(e) => setCustomTopic(e.target.value)}
                  placeholder="e.g. Backpropagation, Dynamic Programming, TCP/IP Handshake..."
                  className="w-full text-sm border border-slate-300 rounded-xl p-2.5 bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}

            {/* Summarizer Mode */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-2">Summarizer Format / Mode</label>
              <div className="space-y-2">
                {MODES.map((m) => (
                  <label
                    key={m.id}
                    className={`flex items-start gap-3 p-2.5 rounded-xl border text-xs cursor-pointer transition-all ${
                      mode === m.id
                        ? 'bg-blue-50/80 border-blue-400 text-blue-900 font-semibold'
                        : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <input
                      type="radio"
                      name="mode"
                      value={m.id}
                      checked={mode === m.id}
                      onChange={(e) => setMode(e.target.value)}
                      className="mt-0.5 text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <span className="font-bold block text-sm">{m.label}</span>
                      <span className="text-[11px] text-slate-500 block">{m.desc}</span>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Difficulty */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">Target Difficulty</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-xl p-2.5 bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
              >
                <option value="Basic">Basic (Introductory, jargon-free)</option>
                <option value="Intermediate">Intermediate (Undergraduate standard)</option>
                <option value="Advanced">Advanced (Nuanced, exam-level depth)</option>
              </select>
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={loading || (sourceType === 'document' && !selectedDocId) || (sourceType === 'topic' && !customTopic.trim())}
              className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold text-sm flex items-center justify-center gap-2 transition-colors shadow-md shadow-blue-500/20"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating with Ollama...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Generate Summary
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right: Summary Output Panel */}
        <div className="lg:col-span-7">
          <div className="glass-card p-6 min-h-[520px] flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-base text-slate-900">Generated Summary</span>
                  {summary && (
                    <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-800 text-[11px] font-bold uppercase">
                      {mode.replace('_', ' ')}
                    </span>
                  )}
                </div>

                {summary && (
                  <button
                    onClick={handleCopy}
                    className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                )}
              </div>

              {error && (
                <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-sm flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                  <div className="text-xs">{error}</div>
                </div>
              )}

              {loading ? (
                <div className="py-24 text-center space-y-3">
                  <Loader2 className="w-10 h-10 text-blue-600 animate-spin mx-auto" />
                  <p className="text-sm font-semibold text-slate-700">Synthesizing revision notes with Ollama...</p>
                  <p className="text-xs text-slate-500">Extracting key concepts, formulas, and definitions.</p>
                </div>
              ) : summary ? (
                <div className="prose prose-slate max-w-none text-sm leading-relaxed whitespace-pre-wrap font-sans text-slate-800">
                  {summary}
                </div>
              ) : (
                <div className="py-24 text-center text-slate-400 text-sm">
                  Select a document or enter a topic on the left and click "Generate Summary" to view your structured revision notes here.
                </div>
              )}
            </div>

            {summary && (
              <div className="mt-6 pt-4 border-t border-slate-100 text-right text-xs text-slate-500">
                Generated using local Ollama ({difficulty} level)
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
export default SummarizerPage
