import React, { useState, useEffect } from 'react'
import {
  HelpCircle,
  Sparkles,
  CheckCircle,
  XCircle,
  Award,
  Loader2,
  AlertCircle,
  RotateCcw,
  FileText,
  Bookmark,
} from 'lucide-react'
import { getMockQuiz, scoreQuiz, listDocuments } from '../api/apiService'
import type { DocumentItem, QuizQuestion, QuizScoreResult } from '../types'

export const QuizGeneratorPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [sourceType, setSourceType] = useState<'document' | 'topic'>('document')
  const [selectedDocId, setSelectedDocId] = useState<string>('')
  const [customTopic, setCustomTopic] = useState<string>('')
  const [difficulty, setDifficulty] = useState<string>('Intermediate')
  const [numQuestions, setNumQuestions] = useState<number>(5)

  const [loading, setLoading] = useState(false)
  const [scoring, setScoring] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [questions, setQuestions] = useState<QuizQuestion[]>([])
  const [userAnswers, setUserAnswers] = useState<Record<string, string>>({})
  const [scoreResult, setScoreResult] = useState<QuizScoreResult | null>(null)

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
    setQuestions([])
    setUserAnswers({})
    setScoreResult(null)
    setLoading(true)

    try {
      const res = await getMockQuiz({
        doc_id: sourceType === 'document' ? selectedDocId || undefined : undefined,
        topic: sourceType === 'topic' ? customTopic || undefined : undefined,
        difficulty,
        question_type: 'mcq',
        num_questions: numQuestions,
      })
      setQuestions(res.questions || [])
    } catch (err: any) {
      console.error(err)
      setError(
        err.response?.data?.detail ||
          'Failed to generate quiz. Make sure Ollama is running and model llama3.2 is available.'
      )
    } finally {
      setLoading(false)
    }
  }

  const handleSelectOption = (questionId: string | number, optionKey: string) => {
    if (scoreResult) return // Quiz already graded
    setUserAnswers((prev) => ({
      ...prev,
      [String(questionId)]: optionKey,
    }))
  }

  const handleSubmitQuiz = async () => {
    if (questions.length === 0) return

    setScoring(true)
    setError(null)

    try {
      const answersPayload = questions.map((q) => ({
        question_id: q.id,
        selected_option: userAnswers[String(q.id)] || '',
      }))

      const result = await scoreQuiz({
        doc_id: sourceType === 'document' ? selectedDocId : undefined,
        topic: sourceType === 'topic' ? customTopic : 'Document Quiz',
        difficulty,
        questions,
        answers: answersPayload,
      })
      setScoreResult(result)
    } catch (err: any) {
      console.error(err)
      setError(err.response?.data?.detail || 'Failed to score quiz.')
    } finally {
      setScoring(false)
    }
  }

  const handleResetQuiz = () => {
    setScoreResult(null)
    setUserAnswers({})
  }

  const allAnswered = questions.length > 0 && questions.every((q) => Boolean(userAnswers[String(q.id)]))

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Title */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 flex items-center gap-2.5">
          <HelpCircle className="w-8 h-8 text-blue-600" />
          Interactive Exam Quiz Generator
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          Generate realistic practice exam MCQs from your notes or typed subjects. Scored algorithmically in Python and saved to your progress dashboard.
        </p>
      </div>

      {/* Setup Form */}
      <form onSubmit={handleGenerate} className="glass-card p-6 mb-8 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          {/* Source Type */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Source
            </label>
            <div className="flex items-center p-1 bg-slate-100 rounded-lg text-xs font-bold">
              <button
                type="button"
                onClick={() => setSourceType('document')}
                className={`flex-1 py-1.5 rounded-md transition-all ${
                  sourceType === 'document' ? 'bg-white text-blue-700 shadow-xs' : 'text-slate-600'
                }`}
              >
                Document
              </button>
              <button
                type="button"
                onClick={() => setSourceType('topic')}
                className={`flex-1 py-1.5 rounded-md transition-all ${
                  sourceType === 'topic' ? 'bg-white text-blue-700 shadow-xs' : 'text-slate-600'
                }`}
              >
                Topic
              </button>
            </div>
          </div>

          {/* Target */}
          <div className="md:col-span-2">
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              {sourceType === 'document' ? 'Select Document' : 'Enter Topic'}
            </label>
            {sourceType === 'document' ? (
              <select
                value={selectedDocId}
                onChange={(e) => setSelectedDocId(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg p-2.5 bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
              >
                {documents.map((d) => (
                  <option key={d.doc_id} value={d.doc_id}>
                    {d.filename} ({d.word_count} words)
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={customTopic}
                onChange={(e) => setCustomTopic(e.target.value)}
                placeholder="e.g. Operating Systems Concurrency, Sorting Algorithms..."
                className="w-full text-sm border border-slate-300 rounded-lg p-2.5 bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
              />
            )}
          </div>

          {/* Num Questions & Difficulty */}
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Questions
              </label>
              <select
                value={numQuestions}
                onChange={(e) => setNumQuestions(Number(e.target.value))}
                className="w-full text-sm border border-slate-300 rounded-lg p-2.5 bg-white"
              >
                <option value={3}>3 MCQs</option>
                <option value={5}>5 MCQs</option>
                <option value={10}>10 MCQs</option>
              </select>
            </div>

            <div className="flex-1">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Level
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg p-2.5 bg-white"
              >
                <option value="Basic">Basic</option>
                <option value="Intermediate">Medium</option>
                <option value="Advanced">Exam</option>
              </select>
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || (sourceType === 'document' && !selectedDocId) || (sourceType === 'topic' && !customTopic.trim())}
          className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold text-sm flex items-center justify-center gap-2 transition-colors shadow-md shadow-blue-500/20"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Generating MCQs with Ollama...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Generate Quiz
            </>
          )}
        </button>
      </form>

      {/* Error Banner */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="text-xs">{error}</div>
        </div>
      )}

      {/* Score Banner when Graded */}
      {scoreResult && (
        <div className="glass-card p-6 mb-8 border-2 border-blue-400 bg-gradient-to-r from-blue-50 to-indigo-50 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4 text-center sm:text-left">
            <div className="w-14 h-14 rounded-2xl bg-blue-600 text-white flex items-center justify-center shadow-lg shadow-blue-500/30">
              <Award className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-xl font-black text-slate-900">
                Score: {scoreResult.score_percent}% ({scoreResult.correct_answers} of {scoreResult.total_questions} correct)
              </h2>
              <p className="text-xs text-slate-600 mt-0.5 font-medium">
                Results recorded to SQLite database for real progress tracking.
              </p>
            </div>
          </div>

          <button
            onClick={handleResetQuiz}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold bg-white text-slate-700 border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors shadow-xs"
          >
            <RotateCcw className="w-4 h-4 text-slate-400" />
            Retry Quiz
          </button>
        </div>
      )}

      {/* Quiz Questions List */}
      {questions.length > 0 && (
        <div className="space-y-6">
          {questions.map((q, qIndex) => {
            const qIdStr = String(q.id)
            const gradedInfo = scoreResult?.graded_questions.find((g) => String(g.id) === qIdStr)

            return (
              <div
                key={q.id}
                className={`glass-card p-6 transition-all ${
                  gradedInfo
                    ? gradedInfo.is_correct
                      ? 'border-emerald-300 bg-emerald-50/20'
                      : 'border-red-300 bg-red-50/20'
                    : 'border-slate-200'
                }`}
              >
                <div className="flex items-start justify-between gap-3 mb-4">
                  <h3 className="text-base font-bold text-slate-900">
                    <span className="text-blue-600 mr-2">Q{qIndex + 1}.</span>
                    {q.question}
                  </h3>

                  {gradedInfo && (
                    <div>
                      {gradedInfo.is_correct ? (
                        <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-100 px-2.5 py-1 rounded-full">
                          <CheckCircle className="w-3.5 h-3.5" /> Correct
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs font-bold text-red-700 bg-red-100 px-2.5 py-1 rounded-full">
                          <XCircle className="w-3.5 h-3.5" /> Incorrect
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Options List */}
                <div className="space-y-2.5">
                  {Object.entries(q.options || {}).map(([key, val]) => {
                    const isSelected = userAnswers[qIdStr] === key
                    const isAnswerKey = gradedInfo && gradedInfo.correct_answer === key
                    const isUserWrong = gradedInfo && isSelected && !gradedInfo.is_correct

                    let optionStyle = 'border-slate-200 hover:border-slate-300 bg-white text-slate-800'
                    if (isSelected && !gradedInfo) {
                      optionStyle = 'border-blue-600 bg-blue-50 text-blue-900 font-semibold ring-2 ring-blue-500/20'
                    } else if (isAnswerKey) {
                      optionStyle = 'border-emerald-500 bg-emerald-50 text-emerald-900 font-semibold'
                    } else if (isUserWrong) {
                      optionStyle = 'border-red-400 bg-red-50 text-red-900 line-through'
                    }

                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => handleSelectOption(q.id, key)}
                        disabled={Boolean(scoreResult)}
                        className={`w-full text-left p-3.5 rounded-xl border text-sm flex items-center justify-between transition-all ${optionStyle}`}
                      >
                        <div className="flex items-center gap-3">
                          <span className="w-6 h-6 rounded-lg bg-slate-100 text-slate-700 font-bold text-xs flex items-center justify-center shrink-0">
                            {key}
                          </span>
                          <span>{val}</span>
                        </div>
                        {isAnswerKey && <CheckCircle className="w-4 h-4 text-emerald-600" />}
                        {isUserWrong && <XCircle className="w-4 h-4 text-red-600" />}
                      </button>
                    )
                  })}
                </div>

                {/* Explanation Box */}
                {gradedInfo && (
                  <div className="mt-4 p-3.5 bg-slate-100/70 rounded-xl text-xs text-slate-700 border border-slate-200">
                    <span className="font-bold text-slate-900 block mb-0.5">Explanation:</span>
                    {gradedInfo.explanation}
                  </div>
                )}
              </div>
            )
          })}

          {/* Submit button */}
          {!scoreResult && (
            <div className="text-center pt-2">
              <button
                type="button"
                onClick={handleSubmitQuiz}
                disabled={scoring || !allAnswered}
                className="px-8 py-3.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-black text-sm flex items-center justify-center gap-2 mx-auto transition-colors shadow-lg shadow-blue-500/25"
              >
                {scoring ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Grading Answers in Python...
                  </>
                ) : (
                  <>
                    <Award className="w-4 h-4" />
                    Submit & Grade Answers ({Object.keys(userAnswers).length}/{questions.length} answered)
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
export default QuizGeneratorPage
