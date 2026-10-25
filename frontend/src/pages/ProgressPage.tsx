import React, { useState, useEffect } from 'react'
import {
  BarChart3,
  CheckCircle2,
  Award,
  BookOpen,
  Calendar,
  AlertTriangle,
  Trash2,
  TrendingUp,
  Inbox,
  Loader2,
} from 'lucide-react'
import { getProgress, deleteAllData } from '../api/apiService'
import type { ProgressData } from '../types'

export const ProgressPage: React.FC = () => {
  const [data, setData] = useState<ProgressData | null>(null)
  const [loading, setLoading] = useState(true)
  const [purging, setPurging] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const loadProgress = () => {
    setLoading(true)
    getProgress()
      .then((res) => setData(res))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadProgress()
  }, [])

  const handleDeleteAll = async () => {
    if (
      !window.confirm(
        '⚠️ Are you sure you want to delete ALL your data? This will permanently remove all uploaded documents, vector indices, tasks, quiz scores, and study plans for this session.'
      )
    ) {
      return
    }

    setPurging(true)
    try {
      const res = await deleteAllData()
      setMessage(res.message)
      loadProgress()
    } catch (err: any) {
      console.error(err)
      setMessage('Failed to purge data.')
    } finally {
      setPurging(false)
    }
  }

  if (loading) {
    return (
      <div className="py-32 text-center">
        <Loader2 className="w-10 h-10 text-blue-600 animate-spin mx-auto mb-3" />
        <p className="text-sm font-semibold text-slate-600">Retrieving real progress analytics from SQLite...</p>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 flex items-center gap-2.5">
            <BarChart3 className="w-8 h-8 text-blue-600" />
            Empirical Progress Dashboard
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Real performance tracking derived strictly from your stored SQLite tasks, quiz scores, and study activities.
          </p>
        </div>

        {data?.has_data && (
          <button
            onClick={handleDeleteAll}
            disabled={purging}
            className="flex items-center gap-2 px-4 py-2 text-xs font-bold bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 rounded-xl transition-colors shadow-xs"
          >
            <Trash2 className="w-4 h-4 text-red-600" />
            Delete All My Data
          </button>
        )}
      </div>

      {message && (
        <div className="mb-6 p-4 rounded-xl bg-blue-50 border border-blue-200 text-blue-900 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-blue-600" />
          <span>{message}</span>
        </div>
      )}

      {/* Empty State Banner if no data */}
      {!data?.has_data ? (
        <div className="glass-card p-16 text-center max-w-xl mx-auto my-8 space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto shadow-inner">
            <Inbox className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">No Learning Activity Recorded Yet</h2>
            <p className="text-sm text-slate-500 mt-1">
              StudyOS adheres to strict academic honesty: zero synthetic or fabricated metrics. Once you complete tasks, take quizzes, or upload documents, your real analytics will populate here.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Top Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Task Completion Rate */}
            <div className="glass-card p-5">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider">Task Completion</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="text-3xl font-black text-slate-900">{data.tasks.completion_rate}%</div>
              <p className="text-xs text-slate-500 mt-1 font-medium">
                {data.tasks.completed} of {data.tasks.total} tasks completed
              </p>
            </div>

            {/* Quiz Average */}
            <div className="glass-card p-5">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider">Quiz Average</span>
                <Award className="w-4 h-4 text-blue-600" />
              </div>
              <div className="text-3xl font-black text-slate-900">{data.quizzes.average_score}%</div>
              <p className="text-xs text-slate-500 mt-1 font-medium">
                Across {data.quizzes.total_taken} completed quiz attempts
              </p>
            </div>

            {/* Highest Score */}
            <div className="glass-card p-5">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider">Highest Quiz Score</span>
                <TrendingUp className="w-4 h-4 text-indigo-600" />
              </div>
              <div className="text-3xl font-black text-indigo-600">{data.quizzes.highest_score}%</div>
              <p className="text-xs text-slate-500 mt-1 font-medium">Top exam simulation result</p>
            </div>

            {/* Uploaded Materials */}
            <div className="glass-card p-5">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider">Indexed Documents</span>
                <BookOpen className="w-4 h-4 text-slate-600" />
              </div>
              <div className="text-3xl font-black text-slate-900">{data.activity.documents_uploaded}</div>
              <p className="text-xs text-slate-500 mt-1 font-medium">
                {data.activity.plans_generated} study timetable(s) created
              </p>
            </div>
          </div>

          {/* Topic-Wise Performance */}
          <div className="glass-card p-6">
            <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Award className="w-5 h-5 text-blue-600" />
              Topic-Wise Quiz Performance Breakdown
            </h2>

            {data.quizzes.topic_performance.length === 0 ? (
              <p className="text-sm text-slate-500 py-6 text-center">
                Take a practice quiz in "Quiz Generator" to see topic mastery statistics.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider">
                    <tr>
                      <th className="p-3 font-bold rounded-l-lg">Topic</th>
                      <th className="p-3 font-bold">Attempts</th>
                      <th className="p-3 font-bold">Average Score</th>
                      <th className="p-3 font-bold rounded-r-lg">Highest Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.quizzes.topic_performance.map((tp, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="p-3 font-bold text-slate-900">{tp.topic}</td>
                        <td className="p-3 text-slate-600">{tp.attempts}</td>
                        <td className="p-3">
                          <span
                            className={`font-extrabold px-2 py-0.5 rounded text-xs ${
                              tp.average_score >= 80
                                ? 'bg-emerald-50 text-emerald-700'
                                : tp.average_score >= 60
                                ? 'bg-blue-50 text-blue-700'
                                : 'bg-amber-50 text-amber-700'
                            }`}
                          >
                            {tp.average_score}%
                          </span>
                        </td>
                        <td className="p-3 font-bold text-slate-900">{tp.highest_score}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Recent Quiz Attempts */}
          {data.quizzes.recent.length > 0 && (
            <div className="glass-card p-6">
              <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-blue-600" />
                Recent Graded Quiz Attempts
              </h2>
              <div className="space-y-3">
                {data.quizzes.recent.map((q) => (
                  <div
                    key={q.id}
                    className="p-3.5 bg-slate-50 rounded-xl flex items-center justify-between border border-slate-200 text-xs"
                  >
                    <div>
                      <span className="font-bold text-sm text-slate-900 block">{q.topic}</span>
                      <span className="text-slate-500">
                        {q.difficulty} • {q.correct_answers} of {q.total_questions} correct
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-base font-black text-blue-700 block">{q.score_percent}%</span>
                      <span className="text-[11px] text-slate-400">
                        {q.created_at ? new Date(q.created_at).toLocaleDateString() : ''}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
export default ProgressPage
