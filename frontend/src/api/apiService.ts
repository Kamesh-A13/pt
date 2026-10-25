/**
 * apiService.ts — Typed Axios client for StudyOS backend.
 * Uses anonymous session ID in X-Session-ID header.
 * No API keys or tokens required.
 */

import axios from 'axios'
import type {
  ChatResponse,
  DocumentItem,
  HealthStatus,
  ProgressData,
  QuizQuestion,
  QuizScoreResult,
  StudyPlanRecord,
  TaskItem,
  TaskStats,
} from '../types'

// Retrieve or generate anonymous session ID
export function getOrCreateSessionId(): string {
  let sid = localStorage.getItem('studyos_session_id')
  if (!sid) {
    sid = 'user_' + Math.random().toString(36).substring(2, 10) + Date.now().toString(36)
    localStorage.setItem('studyos_session_id', sid)
  }
  return sid
}

export function resetSessionId(): string {
  const newSid = 'user_' + Math.random().toString(36).substring(2, 10) + Date.now().toString(36)
  localStorage.setItem('studyos_session_id', newSid)
  return newSid
}

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
})

// Attach session ID header to every request
API.interceptors.request.use((config) => {
  const sessionId = getOrCreateSessionId()
  config.headers['X-Session-ID'] = sessionId
  return config
})

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------
export async function getHealth(): Promise<HealthStatus> {
  const res = await API.get<HealthStatus>('/health')
  return res.data
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------
export interface UploadResult {
  doc_id: string
  filename: string
  char_count: number
  word_count: number
  preview: string
  full_text: string
}

export async function uploadDocument(file: File): Promise<UploadResult> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await API.post<UploadResult>('/api/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const res = await API.get<{ documents: DocumentItem[] }>('/api/documents')
  return res.data.documents
}

export async function deleteDocument(docId: string): Promise<{ message: string }> {
  const res = await API.delete<{ message: string }>(`/api/documents/${docId}`)
  return res.data
}

export async function deleteAllData(): Promise<{ message: string; purged: Record<string, number> }> {
  const res = await API.delete<{ message: string; purged: Record<string, number> }>('/api/data')
  return res.data
}

// ---------------------------------------------------------------------------
// Summarization & Generation
// ---------------------------------------------------------------------------
export interface SummarizeParams {
  doc_id?: string
  text?: string
  topic?: string
  difficulty?: string
  mode?: string
}

export async function getSummary(params: SummarizeParams): Promise<{ summary: string; mode: string }> {
  const res = await API.post<{ summary: string; mode: string }>('/api/summarize', params)
  return res.data
}

export async function getFlashcards(
  docId: string,
  difficulty = 'Intermediate',
  numCards = 15,
): Promise<{ flashcards: Array<{ front: string; back: string }> }> {
  const res = await API.post<{ flashcards: Array<{ front: string; back: string }> }>('/api/flashcards', {
    doc_id: docId,
    difficulty,
    num_cards: numCards,
  })
  return res.data
}

export async function getFAQs(
  docId: string,
  difficulty = 'Intermediate',
  numFaqs = 10,
): Promise<{ faqs: Array<{ question: string; answer: string }> }> {
  const res = await API.post<{ faqs: Array<{ question: string; answer: string }> }>('/api/faq', {
    doc_id: docId,
    difficulty,
    num_faqs: numFaqs,
  })
  return res.data
}

// ---------------------------------------------------------------------------
// Quiz Generation & Scoring
// ---------------------------------------------------------------------------
export interface MockQuizParams {
  doc_id?: string
  topic?: string
  text?: string
  difficulty?: string
  question_type?: string
  num_questions?: number
}

export async function getMockQuiz(params: MockQuizParams): Promise<{ questions: QuizQuestion[] }> {
  const res = await API.post<{ questions: QuizQuestion[] }>('/api/mock-quiz', params)
  return res.data
}

export interface ScoreQuizParams {
  doc_id?: string
  topic?: string
  difficulty?: string
  questions: QuizQuestion[]
  answers: Array<{ question_id: number | string; selected_option: string }>
}

export async function scoreQuiz(params: ScoreQuizParams): Promise<QuizScoreResult> {
  const res = await API.post<QuizScoreResult>('/api/quiz/score', params)
  return res.data
}

// ---------------------------------------------------------------------------
// Chat (Document & General Study)
// ---------------------------------------------------------------------------
export interface ChatParams {
  doc_id?: string | null
  subject?: string | null
  message: string
  history?: Array<{ role: string; content: string }>
  mode?: string
}

export async function sendChatMessage(params: ChatParams): Promise<ChatResponse> {
  const res = await API.post<ChatResponse>('/api/chat', params)
  return res.data
}

// ---------------------------------------------------------------------------
// Task Manager
// ---------------------------------------------------------------------------
export async function listTasks(status?: string): Promise<{ tasks: TaskItem[]; stats: TaskStats }> {
  const res = await API.get<{ tasks: TaskItem[]; stats: TaskStats }>('/api/tasks', {
    params: status ? { status } : undefined,
  })
  return res.data
}

export async function createTask(data: { title: string; description?: string; deadline?: string }): Promise<TaskItem> {
  const res = await API.post<TaskItem>('/api/tasks', data)
  return res.data
}

export async function toggleTask(taskId: string): Promise<TaskItem> {
  const res = await API.patch<TaskItem>(`/api/tasks/${taskId}/toggle`)
  return res.data
}

export async function deleteTask(taskId: string): Promise<{ message: string }> {
  const res = await API.delete<{ message: string }>(`/api/tasks/${taskId}`)
  return res.data
}

// ---------------------------------------------------------------------------
// Study Planner
// ---------------------------------------------------------------------------
export interface StudyPlanRequest {
  subjects: string[]
  exam_dates: Record<string, string>
  daily_hours: number
  topics: Record<string, string[]>
}

export async function generateStudyPlan(data: StudyPlanRequest): Promise<StudyPlanRecord> {
  const res = await API.post<StudyPlanRecord>('/api/planner/generate', data)
  return res.data
}

export async function getLatestStudyPlan(): Promise<StudyPlanRecord | { plan: null; message: string }> {
  const res = await API.get<StudyPlanRecord | { plan: null; message: string }>('/api/planner')
  return res.data
}

export async function convertPlanToTasks(): Promise<{ message: string; tasks_created: number }> {
  const res = await API.post<{ message: string; tasks_created: number }>('/api/planner/convert-to-tasks')
  return res.data
}

// ---------------------------------------------------------------------------
// Progress Dashboard
// ---------------------------------------------------------------------------
export async function getProgress(): Promise<ProgressData> {
  const res = await API.get<ProgressData>('/api/progress')
  return res.data
}
