/**
 * TypeScript interfaces and types for StudyOS
 */

export interface DocumentItem {
  id: string
  doc_id: string
  filename: string
  char_count: number
  word_count: number
  created_at: string
}

export interface TaskItem {
  id: string
  title: string
  description: string
  deadline: string | null
  completed: boolean
  completed_at: string | null
  created_at: string
  is_overdue?: boolean
}

export interface TaskStats {
  total: number
  completed: number
  pending: number
  overdue: number
  upcoming: number
}

export interface QuizQuestion {
  id: number | string
  type: string
  question: string
  options: Record<string, string>
  correct_answer?: string
  explanation?: string
}

export interface GradedQuestion {
  id: number | string
  question: string
  options: Record<string, string>
  user_answer: string
  correct_answer: string
  is_correct: boolean
  explanation: string
}

export interface QuizScoreResult {
  result_id: string
  total_questions: number
  correct_answers: number
  score_percent: number
  graded_questions: GradedQuestion[]
  created_at: string
}

export interface StudySession {
  subject: string
  topic: string
  duration_minutes: number
  priority?: string
  notes?: string
}

export interface StudyDayPlan {
  date: string
  sessions: StudySession[]
}

export interface StudyPlanData {
  plan: StudyDayPlan[]
  summary?: string
  tips?: string[]
  disclaimer?: string
}

export interface StudyPlanRecord {
  id: string
  session_id: string
  subjects: string[]
  exam_dates: Record<string, string>
  daily_hours: number
  plan: StudyPlanData
  created_at: string
}

export interface TopicPerformance {
  topic: string
  attempts: number
  average_score: number
  highest_score: number
}

export interface RecentQuizAttempt {
  id: string
  topic: string
  difficulty: string
  score_percent: number
  correct_answers: number
  total_questions: number
  created_at: string
}

export interface ProgressData {
  has_data: boolean
  tasks: {
    total: number
    completed: number
    pending: number
    completion_rate: number
  }
  quizzes: {
    total_taken: number
    average_score: number
    highest_score: number
    recent: RecentQuizAttempt[]
    topic_performance: TopicPerformance[]
  }
  activity: {
    documents_uploaded: number
    plans_generated: number
  }
}

export interface ChatSource {
  source: string
  page: number
  score: number
}

export interface ChatResponse {
  response: string
  doc_id?: string | null
  subject?: string
  sources: ChatSource[]
  mode: string
}

export interface HealthStatus {
  status: string
  message: string
  version: string
  llm_provider: string
  features: string[]
  ollama: {
    ollama_reachable: boolean
    ollama_url?: string
    model?: string
    model_available?: boolean
    available_models?: string[]
    error?: string
  }
}
