import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import ChatPage from './pages/ChatPage'
import DocumentsPage from './pages/DocumentsPage'
import SummarizerPage from './pages/SummarizerPage'
import QuizGeneratorPage from './pages/QuizGeneratorPage'
import StudyPlannerPage from './pages/StudyPlannerPage'
import TaskManagerPage from './pages/TaskManagerPage'
import ProgressPage from './pages/ProgressPage'

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/20 text-slate-800 flex flex-col font-sans">
      <Navbar />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>
      <footer className="border-t border-slate-200/80 bg-white/70 py-4 text-center text-xs text-slate-500">
        <p>
          StudyOS &copy; {new Date().getFullYear()} &bull; AI-Powered Student Assistant &bull; Local Ollama RAG &bull; Zero API Keys
        </p>
      </footer>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/notes" element={<DocumentsPage />} />
          <Route path="/summarize" element={<SummarizerPage />} />
          <Route path="/quiz" element={<QuizGeneratorPage />} />
          <Route path="/planner" element={<StudyPlannerPage />} />
          <Route path="/tasks" element={<TaskManagerPage />} />
          <Route path="/progress" element={<ProgressPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
