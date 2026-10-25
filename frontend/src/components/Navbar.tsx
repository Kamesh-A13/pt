import React, { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  MessageSquare,
  FileText,
  FileCode,
  HelpCircle,
  Calendar,
  CheckSquare,
  BarChart3,
  Menu,
  X,
  Sparkles,
  Server,
  RefreshCw,
} from 'lucide-react'
import { getHealth, getOrCreateSessionId, resetSessionId } from '../api/apiService'
import type { HealthStatus } from '../types'

interface NavbarProps {
  onSessionReset?: () => void
}

export const Navbar: React.FC<NavbarProps> = ({ onSessionReset }) => {
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [sessionId, setSessionId] = useState(getOrCreateSessionId())

  useEffect(() => {
    getHealth()
      .then((data) => setHealth(data))
      .catch(() => setHealth(null))
  }, [])

  const handleResetSession = () => {
    if (window.confirm('Reset your anonymous session? This creates a clean session for new documents and tasks.')) {
      const newSid = resetSessionId()
      setSessionId(newSid)
      if (onSessionReset) onSessionReset()
      window.location.reload()
    }
  }

  const navItems = [
    { path: '/chat', label: 'AI Chat', icon: MessageSquare },
    { path: '/notes', label: 'PDF Notes', icon: FileText },
    { path: '/summarize', label: 'Summarization', icon: FileCode },
    { path: '/quiz', label: 'Quiz Generator', icon: HelpCircle },
    { path: '/planner', label: 'Study Planner', icon: Calendar },
    { path: '/tasks', label: 'Task Manager', icon: CheckSquare },
    { path: '/progress', label: 'Progress Reports', icon: BarChart3 },
  ]

  const ollamaOnline = Boolean(health?.ollama?.ollama_reachable && health?.ollama?.model_available)

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-700 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform">
              <Sparkles className="w-5 h-5 text-blue-100" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-extrabold text-xl tracking-tight text-slate-900">Study<span className="text-blue-600">OS</span></span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-800">Ollama</span>
              </div>
              <p className="text-[11px] text-slate-500 hidden sm:block -mt-1 font-medium">AI Student Assistant</p>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const active = location.pathname === item.path || (item.path === '/chat' && location.pathname === '/')
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold transition-all ${
                    active
                      ? 'bg-blue-50 text-blue-700 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${active ? 'text-blue-600' : 'text-slate-400'}`} />
                  {item.label}
                </Link>
              )
            })}
          </nav>

          {/* Right Status Badges */}
          <div className="hidden sm:flex items-center gap-3">
            {/* Ollama Health Pill */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${
                ollamaOnline
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-amber-50 text-amber-700 border-amber-200'
              }`}
              title={ollamaOnline ? `Connected to Ollama (${health?.ollama?.model})` : 'Ollama not detected at localhost:11434'}
            >
              <Server className="w-3.5 h-3.5" />
              <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
              <span>{ollamaOnline ? `Ollama: ${health?.ollama?.model || 'llama3.2'}` : 'Ollama Offline'}</span>
            </div>

            {/* Session Pill */}
            <button
              onClick={handleResetSession}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors"
              title="Click to reset anonymous session"
            >
              <span>{sessionId.slice(0, 10)}...</span>
              <RefreshCw className="w-3 h-3 text-slate-400 hover:rotate-180 transition-transform" />
            </button>
          </div>

          {/* Mobile menu button */}
          <div className="flex lg:hidden items-center gap-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-600 hover:bg-slate-100 focus:outline-hidden"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu dropdown */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-slate-200 bg-white px-4 pt-3 pb-5 space-y-1 shadow-lg">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = location.pathname === item.path || (item.path === '/chat' && location.pathname === '/')
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-base font-semibold ${
                  active ? 'bg-blue-50 text-blue-700' : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                <Icon className={`w-5 h-5 ${active ? 'text-blue-600' : 'text-slate-400'}`} />
                {item.label}
              </Link>
            )
          })}
          
          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Session: {sessionId.slice(0, 12)}</span>
            <button
              onClick={handleResetSession}
              className="text-blue-600 font-semibold hover:underline"
            >
              Reset Session
            </button>
          </div>
        </div>
      )}
    </header>
  )
}
export default Navbar
