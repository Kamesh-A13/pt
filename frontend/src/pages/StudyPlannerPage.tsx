import React, { useState, useEffect } from 'react'
import {
  Calendar,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Clock,
  ArrowRight,
  ListPlus,
  Trash2,
  Plus,
} from 'lucide-react'
import { generateStudyPlan, getLatestStudyPlan, convertPlanToTasks } from '../api/apiService'
import type { StudyPlanRecord } from '../types'

export const StudyPlannerPage: React.FC = () => {
  const [subjects, setSubjects] = useState<string[]>(['Data Structures', 'Computer Networks'])
  const [newSubject, setNewSubject] = useState('')
  const [examDates, setExamDates] = useState<Record<string, string>>({
    'Data Structures': '2026-11-20',
    'Computer Networks': '2026-11-28',
  })
  const [dailyHours, setDailyHours] = useState(4.0)
  const [topicsInput, setTopicsInput] = useState<Record<string, string>>({
    'Data Structures': 'Trees, Graphs, Dynamic Programming, Hash Tables',
    'Computer Networks': 'OSI Model, TCP/IP, Routing Algorithms, DNS',
  })

  const [loading, setLoading] = useState(false)
  const [converting, setConverting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [currentPlan, setCurrentPlan] = useState<StudyPlanRecord | null>(null)

  useEffect(() => {
    getLatestStudyPlan()
      .then((res: any) => {
        if (res && res.plan) {
          setCurrentPlan(res)
        }
      })
      .catch((err) => console.error(err))
  }, [])

  const handleAddSubject = (e: React.FormEvent) => {
    e.preventDefault()
    const s = newSubject.trim()
    if (!s || subjects.includes(s)) return
    setSubjects([...subjects, s])
    setExamDates({ ...examDates, [s]: '' })
    setTopicsInput({ ...topicsInput, [s]: '' })
    setNewSubject('')
  }

  const handleRemoveSubject = (s: string) => {
    setSubjects(subjects.filter((sub) => sub !== s))
    const dCopy = { ...examDates }
    delete dCopy[s]
    setExamDates(dCopy)
  }

  const handleGeneratePlan = async () => {
    if (subjects.length === 0) {
      setError('Please add at least one subject.')
      return
    }

    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const formattedTopics: Record<string, string[]> = {}
      for (const s of subjects) {
        const raw = topicsInput[s] || ''
        formattedTopics[s] = raw
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean)
      }

      const res = await generateStudyPlan({
        subjects,
        exam_dates: examDates,
        daily_hours: dailyHours,
        topics: formattedTopics,
      })
      setCurrentPlan(res)
      setSuccess('Personalized study plan generated successfully!')
    } catch (err: any) {
      console.error(err)
      setError(
        err.response?.data?.detail ||
          'Failed to generate study plan with Ollama. Make sure Ollama is running and model llama3.2 is available.'
      )
    } finally {
      setLoading(false)
    }
  }

  const handleConvertToTasks = async () => {
    setConverting(true)
    setError(null)
    setSuccess(null)

    try {
      const res = await convertPlanToTasks()
      setSuccess(`Created ${res.tasks_created} study sessions as actionable tasks in Task Manager!`)
    } catch (err: any) {
      console.error(err)
      setError(err.response?.data?.detail || 'Failed to convert plan to tasks.')
    } finally {
      setConverting(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Title */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 flex items-center gap-2.5">
          <Calendar className="w-8 h-8 text-blue-600" />
          Smart AI Study Planner
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          Input your subjects, upcoming exam dates, daily study bandwidth, and target topics. Ollama calculates an optimized, realistic daily revision timetable.
        </p>
      </div>

      {/* Alerts */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="text-xs">{error}</div>
        </div>
      )}

      {success && (
        <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <div className="text-xs font-semibold">{success}</div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Input Form */}
        <div className="lg:col-span-5 space-y-6">
          <div className="glass-card p-6 space-y-5">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-600" />
              Study Inputs & Exam Schedule
            </h2>

            {/* Daily Hours Slider */}
            <div>
              <div className="flex items-center justify-between text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                <span>Daily Study Bandwidth</span>
                <span className="text-blue-600 font-extrabold text-sm">{dailyHours} Hours/Day</span>
              </div>
              <input
                type="range"
                min="1"
                max="12"
                step="0.5"
                value={dailyHours}
                onChange={(e) => setDailyHours(parseFloat(e.target.value))}
                className="w-full accent-blue-600 cursor-pointer"
              />
            </div>

            {/* Add Subject */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Subjects & Target Topics
              </label>
              <form onSubmit={handleAddSubject} className="flex gap-2 mb-3">
                <input
                  type="text"
                  value={newSubject}
                  onChange={(e) => setNewSubject(e.target.value)}
                  placeholder="Add a subject (e.g. Operating Systems)..."
                  className="flex-1 text-sm border border-slate-300 rounded-xl p-2 bg-white"
                />
                <button
                  type="submit"
                  className="px-3.5 py-2 rounded-xl bg-slate-900 text-white font-bold text-xs flex items-center gap-1 hover:bg-slate-800 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  Add
                </button>
              </form>

              {/* Subject List */}
              <div className="space-y-3.5">
                {subjects.map((s) => (
                  <div key={s} className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sm text-slate-900">{s}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveSubject(s)}
                        className="text-slate-400 hover:text-red-600"
                        title="Remove"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <div>
                        <span className="text-[11px] font-semibold text-slate-500 block mb-0.5">Exam Date</span>
                        <input
                          type="date"
                          value={examDates[s] || ''}
                          onChange={(e) => setExamDates({ ...examDates, [s]: e.target.value })}
                          className="w-full text-xs border border-slate-300 rounded-lg p-1.5 bg-white"
                        />
                      </div>
                      <div>
                        <span className="text-[11px] font-semibold text-slate-500 block mb-0.5">Key Topics</span>
                        <input
                          type="text"
                          value={topicsInput[s] || ''}
                          onChange={(e) => setTopicsInput({ ...topicsInput, [s]: e.target.value })}
                          placeholder="comma separated"
                          className="w-full text-xs border border-slate-300 rounded-lg p-1.5 bg-white"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Generate Button */}
            <button
              type="button"
              onClick={handleGeneratePlan}
              disabled={loading || subjects.length === 0}
              className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold text-sm flex items-center justify-center gap-2 transition-colors shadow-md shadow-blue-500/20"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Computing Schedule with Ollama...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Generate 14-Day Study Plan
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right: Plan Display */}
        <div className="lg:col-span-7">
          {currentPlan && currentPlan.plan ? (
            <div className="space-y-6">
              {/* Disclaimer Banner */}
              <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 text-blue-900 text-xs flex items-start gap-3">
                <Sparkles className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold block">AI-Generated Suggestion</span>
                  <p className="mt-0.5 text-blue-800">
                    {currentPlan.plan.disclaimer ||
                      'This timetable is an AI-generated suggestion optimized for balanced study and revision.'}
                  </p>
                </div>
              </div>

              {/* Action Toolbar */}
              <div className="glass-card p-4 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-sm text-slate-900">Active Study Timetable</h3>
                  <p className="text-xs text-slate-500">
                    {currentPlan.subjects?.join(', ')} • {currentPlan.daily_hours} hrs/day
                  </p>
                </div>

                <button
                  type="button"
                  onClick={handleConvertToTasks}
                  disabled={converting}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold text-xs transition-colors shadow-sm"
                >
                  {converting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <ListPlus className="w-3.5 h-3.5" />
                  )}
                  Export to Task Manager
                </button>
              </div>

              {/* Days List */}
              <div className="space-y-4">
                {(currentPlan.plan.plan || []).map((day, dIdx) => (
                  <div key={dIdx} className="glass-card p-5">
                    <div className="flex items-center justify-between mb-3 border-b border-slate-100 pb-2">
                      <span className="font-bold text-sm text-blue-700 flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        Day {dIdx + 1} ({day.date || 'Scheduled'})
                      </span>
                      <span className="text-xs text-slate-500 font-medium">
                        {(day.sessions || []).reduce((acc, s) => acc + (s.duration_minutes || 0), 0)} mins total
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {(day.sessions || []).map((sess, sIdx) => (
                        <div key={sIdx} className="p-3 bg-white border border-slate-200 rounded-xl text-xs space-y-1">
                          <div className="flex items-center justify-between font-bold">
                            <span className="text-slate-900">{sess.subject}</span>
                            <span className="text-blue-600 bg-blue-50 px-2 py-0.5 rounded font-semibold text-[11px]">
                              {sess.duration_minutes}m
                            </span>
                          </div>
                          <div className="text-slate-600 font-medium">{sess.topic}</div>
                          {sess.notes && (
                            <div className="text-[11px] text-slate-500 italic mt-1">Note: {sess.notes}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="glass-card p-12 text-center text-slate-400 text-sm">
              <Calendar className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              Configure your subjects, exam dates, and daily hours on the left to generate your custom AI study schedule.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
export default StudyPlannerPage
