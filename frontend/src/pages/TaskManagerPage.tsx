import React, { useState, useEffect } from 'react'
import {
  CheckSquare,
  Plus,
  Trash2,
  Calendar,
  AlertCircle,
  Clock,
  CheckCircle2,
  Filter,
} from 'lucide-react'
import { listTasks, createTask, toggleTask, deleteTask } from '../api/apiService'
import type { TaskItem, TaskStats } from '../types'

export const TaskManagerPage: React.FC = () => {
  const [tasks, setTasks] = useState<TaskItem[]>([])
  const [stats, setStats] = useState<TaskStats>({
    total: 0,
    completed: 0,
    pending: 0,
    overdue: 0,
    upcoming: 0,
  })
  const [filter, setFilter] = useState<string>('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // New task form state
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [deadline, setDeadline] = useState('')

  const loadTasks = () => {
    setLoading(true)
    listTasks(filter === 'all' ? undefined : filter)
      .then((data) => {
        setTasks(data.tasks)
        setStats(data.stats)
      })
      .catch((err) => {
        console.error(err)
        setError('Failed to load tasks.')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadTasks()
  }, [filter])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return

    try {
      await createTask({
        title: title.trim(),
        description: description.trim() || undefined,
        deadline: deadline || undefined,
      })
      setTitle('')
      setDescription('')
      setDeadline('')
      loadTasks()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create task.')
    }
  }

  const handleToggle = async (id: string) => {
    try {
      await toggleTask(id)
      loadTasks()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update task.')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteTask(id)
      loadTasks()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete task.')
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Title */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 flex items-center gap-2.5">
          <CheckSquare className="w-8 h-8 text-blue-600" />
          Study Task Manager
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          Organize your revision assignments, problem sets, and reading deadlines with persistent SQLite tracking.
        </p>
      </div>

      {/* Stats Cards Row */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
        <div className="glass-card p-4 text-center">
          <span className="text-2xl font-black text-slate-900">{stats.total}</span>
          <span className="text-xs font-bold text-slate-500 block">Total</span>
        </div>
        <div className="glass-card p-4 text-center">
          <span className="text-2xl font-black text-emerald-600">{stats.completed}</span>
          <span className="text-xs font-bold text-slate-500 block">Completed</span>
        </div>
        <div className="glass-card p-4 text-center">
          <span className="text-2xl font-black text-blue-600">{stats.pending}</span>
          <span className="text-xs font-bold text-slate-500 block">Pending</span>
        </div>
        <div className="glass-card p-4 text-center">
          <span className="text-2xl font-black text-indigo-600">{stats.upcoming}</span>
          <span className="text-xs font-bold text-slate-500 block">Upcoming</span>
        </div>
        <div className="glass-card p-4 text-center col-span-2 sm:col-span-1">
          <span className="text-2xl font-black text-red-600">{stats.overdue}</span>
          <span className="text-xs font-bold text-slate-500 block">Overdue</span>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="text-xs">{error}</div>
        </div>
      )}

      {/* Create Task Form */}
      <form onSubmit={handleCreate} className="glass-card p-5 mb-6 space-y-3">
        <h2 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
          <Plus className="w-4 h-4 text-blue-600" />
          Add New Study Task
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
          <div className="sm:col-span-6">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Task title (e.g. Solve LeetCode Graphs)..."
              required
              className="w-full text-sm border border-slate-300 rounded-xl p-2.5 bg-white"
            />
          </div>
          <div className="sm:col-span-3">
            <input
              type="date"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-xl p-2.5 bg-white text-slate-700"
            />
          </div>
          <div className="sm:col-span-3">
            <button
              type="submit"
              className="w-full h-full py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm flex items-center justify-center gap-1.5 transition-colors shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Add Task
            </button>
          </div>
        </div>
      </form>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-2">
        <Filter className="w-4 h-4 text-slate-400 shrink-0" />
        {['all', 'pending', 'completed', 'upcoming', 'overdue'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`capitalize px-3 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
              filter === f
                ? 'bg-blue-600 text-white shadow-xs'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Task List */}
      <div className="space-y-2.5">
        {tasks.length === 0 ? (
          <div className="glass-card p-12 text-center text-slate-400 text-sm">
            No {filter !== 'all' ? filter : ''} tasks found.
          </div>
        ) : (
          tasks.map((t) => (
            <div
              key={t.id}
              className={`glass-card p-4 flex items-center justify-between gap-3 transition-all ${
                t.completed ? 'opacity-65 bg-slate-50/80' : ''
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <button
                  type="button"
                  onClick={() => handleToggle(t.id)}
                  className={`w-6 h-6 rounded-lg border flex items-center justify-center transition-colors shrink-0 ${
                    t.completed
                      ? 'bg-emerald-600 border-emerald-600 text-white'
                      : 'border-slate-300 hover:border-blue-500 bg-white'
                  }`}
                >
                  {t.completed && <CheckCircle2 className="w-4 h-4" />}
                </button>

                <div className="min-w-0">
                  <h3
                    className={`text-sm font-bold truncate ${
                      t.completed ? 'line-through text-slate-500' : 'text-slate-900'
                    }`}
                  >
                    {t.title}
                  </h3>
                  {t.description && <p className="text-xs text-slate-500 truncate">{t.description}</p>}
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                {t.deadline && (
                  <span
                    className={`inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full ${
                      t.is_overdue
                        ? 'bg-red-50 text-red-700 border border-red-200'
                        : 'bg-blue-50 text-blue-700 border border-blue-100'
                    }`}
                  >
                    <Calendar className="w-3 h-3" />
                    {new Date(t.deadline).toLocaleDateString()}
                  </span>
                )}

                <button
                  type="button"
                  onClick={() => handleDelete(t.id)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                  title="Delete Task"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
export default TaskManagerPage
