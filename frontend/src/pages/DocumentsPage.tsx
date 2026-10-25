import React, { useState, useEffect } from 'react'
import {
  UploadCloud,
  FileText,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  BookOpen,
  FileCheck,
} from 'lucide-react'
import { uploadDocument, listDocuments, deleteDocument } from '../api/apiService'
import type { DocumentItem } from '../types'

export const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [uploading, setUploading] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const loadDocs = () => {
    listDocuments()
      .then((docs) => {
        setDocuments(docs)
        if (docs.length > 0 && !selectedDoc) {
          setSelectedDoc(docs[0])
        }
      })
      .catch((err) => console.error(err))
  }

  useEffect(() => {
    loadDocs()
  }, [])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError(null)
    setSuccess(null)

    try {
      const result = await uploadDocument(file)
      setSuccess(`Successfully uploaded and indexed "${result.filename}" (${result.word_count} words).`)
      loadDocs()
    } catch (err: any) {
      console.error(err)
      setError(
        err.response?.data?.detail ||
          'Failed to upload document. Please ensure it is a valid non-empty PDF, DOCX, or PPTX under 20MB.'
      )
    } finally {
      setUploading(false)
      // reset file input
      e.target.value = ''
    }
  }

  const handleDelete = async (docId: string, filename: string) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}" and its vector index?`)) return

    try {
      await deleteDocument(docId)
      setDocuments((prev) => prev.filter((d) => d.doc_id !== docId))
      if (selectedDoc?.doc_id === docId) {
        setSelectedDoc(null)
      }
      setSuccess(`Deleted "${filename}".`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete document.')
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Title */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 flex items-center gap-2.5">
          <BookOpen className="w-8 h-8 text-blue-600" />
          PDF & Lecture Notes Repository
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          Upload your course slides, textbooks, and notes. StudyOS automatically extracts text, chunks, and creates an isolated vector index.
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

      {/* Upload Dropzone Card */}
      <div className="glass-card p-6 sm:p-8 mb-8 text-center border-2 border-dashed border-blue-200 hover:border-blue-400 transition-colors">
        <input
          type="file"
          id="doc-upload"
          accept=".pdf,.docx,.pptx"
          onChange={handleFileUpload}
          disabled={uploading}
          className="hidden"
        />
        <label
          htmlFor="doc-upload"
          className="flex flex-col items-center justify-center cursor-pointer group"
        >
          <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-inner">
            {uploading ? (
              <Loader2 className="w-8 h-8 animate-spin" />
            ) : (
              <UploadCloud className="w-8 h-8" />
            )}
          </div>
          <span className="text-base font-bold text-slate-800 group-hover:text-blue-600 transition-colors">
            {uploading ? 'Parsing and embedding document...' : 'Click or drop files to upload'}
          </span>
          <span className="text-xs text-slate-500 mt-1">
            Supports PDF, Word (.docx), and PowerPoint (.pptx) up to 20MB
          </span>
        </label>
      </div>

      {/* Document Grid */}
      <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
        <FileCheck className="w-5 h-5 text-blue-600" />
        Indexed Materials ({documents.length})
      </h2>

      {documents.length === 0 ? (
        <div className="glass-card p-8 text-center text-slate-500 text-sm">
          No documents uploaded yet. Upload a lecture PDF or slides above to begin asking questions and generating revision guides.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {documents.map((doc) => (
            <div
              key={doc.doc_id}
              className="glass-card p-5 flex flex-col justify-between hover:shadow-md transition-shadow"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-bold text-sm text-slate-900 truncate" title={doc.filename}>
                        {doc.filename}
                      </h3>
                      <p className="text-[11px] text-slate-500">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDelete(doc.doc_id, doc.filename)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                    title="Delete document and vector index"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600 font-medium">
                  <span>{doc.word_count.toLocaleString()} words</span>
                  <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-semibold text-[11px] border border-emerald-100">
                    Indexed & Ready
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
export default DocumentsPage
