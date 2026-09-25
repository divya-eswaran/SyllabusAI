import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, Search, FileText, Loader2, CheckCircle2, AlertCircle, X, ChevronRight, Sparkles } from 'lucide-react'
import { uploadPDF, searchSubjects } from '../api'
import toast from 'react-hot-toast'

function UploadZone({ onSuccess }) {
  const [dragging, setDragging] = useState(false)
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null)

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped?.type === 'application/pdf') setFile(dropped)
    else toast.error('Please drop a PDF file')
  }, [])

  const handleFileChange = (e) => {
    const f = e.target.files[0]
    if (f) setFile(f)
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setProgress(0)
    setResult(null)
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await uploadPDF(fd, setProgress)
      setResult(res.data)
      toast.success(`Imported ${res.data.subjects_created} subject(s)!`)
      if (onSuccess) onSuccess(res.data)
    } catch (err) {
      const msg = err.response?.data?.detail || 'Upload failed. Please try again.'
      toast.error(msg)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="glass-card p-8 animate-fade-in">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-primary-600/20 border border-primary-500/30 flex items-center justify-center">
          <Upload className="w-5 h-5 text-primary-400" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-white">Upload Syllabus PDF</h2>
          <p className="text-xs text-slate-500">Extracts all subjects, units & topics automatically</p>
        </div>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-xl p-10 text-center transition-all duration-200 cursor-pointer ${
          dragging
            ? 'border-primary-500 bg-primary-500/10'
            : file
            ? 'border-emerald-500/50 bg-emerald-500/5'
            : 'border-white/10 hover:border-primary-500/40 hover:bg-white/2'
        }`}
        onClick={() => document.getElementById('pdf-input').click()}
      >
        <input
          id="pdf-input"
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleFileChange}
        />
        {file ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 flex items-center justify-center">
              <FileText className="w-7 h-7 text-emerald-400" />
            </div>
            <div>
              <p className="font-semibold text-white text-sm">{file.name}</p>
              <p className="text-xs text-slate-500 mt-0.5">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
            <button
              className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1 mt-1"
              onClick={(e) => { e.stopPropagation(); setFile(null); setResult(null) }}
            >
              <X className="w-3 h-3" /> Remove
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-white/5 flex items-center justify-center">
              <FileText className="w-7 h-7 text-slate-500" />
            </div>
            <div>
              <p className="font-semibold text-slate-300 text-sm">Drop your syllabus PDF here</p>
              <p className="text-xs text-slate-500 mt-1">or click to browse files</p>
            </div>
          </div>
        )}
      </div>

      {/* Progress */}
      {uploading && (
        <div className="mt-4">
          <div className="flex justify-between text-xs text-slate-400 mb-2">
            <span>Processing PDF…</span>
            <span>{progress}%</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="mt-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 animate-fade-in">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span className="text-sm font-semibold text-emerald-300">
              {result.subjects_created} subject(s) imported
            </span>
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            {result.subjects?.map((s) => (
              <span key={s.id} className="badge badge-success text-xs">{s.subject_code} — {s.subject_name}</span>
            ))}
          </div>
        </div>
      )}

      <button
        className="btn-primary w-full mt-5 justify-center"
        onClick={handleUpload}
        disabled={!file || uploading}
      >
        {uploading ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> Processing…</>
        ) : (
          <><Upload className="w-4 h-4" /> Upload & Extract</>
        )}
      </button>
    </div>
  )
}

function SearchSection() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const navigate = useNavigate()

  const handleSearch = async (e) => {
    e?.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    try {
      const res = await searchSubjects(query)
      setResults(res.data)
      if (res.data.total === 0) toast('No subjects found for that query', { icon: '🔍' })
    } catch {
      toast.error('Search failed. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="glass-card p-8 animate-fade-in" style={{ animationDelay: '0.1s' }}>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-accent-600/20 border border-accent-500/30 flex items-center justify-center">
          <Search className="w-5 h-5 text-accent-400" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-white">Search Subjects</h2>
          <p className="text-xs text-slate-500">Find by subject name or code (e.g. IT501)</p>
        </div>
      </div>

      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
          <input
            id="search-input"
            className="input-field pl-10"
            placeholder="Subject name or code…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <button className="btn-accent" type="submit" disabled={loading || !query.trim()}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          Search
        </button>
      </form>

      {/* Results */}
      {results && (
        <div className="mt-5 space-y-3 animate-slide-up">
          {results.total === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No subjects found for "{results.query}"</p>
              <p className="text-xs mt-1">Try uploading the syllabus PDF first</p>
            </div>
          ) : (
            results.results.map((s) => (
              <button
                key={s.id}
                onClick={() => navigate(`/subjects/${s.id}`)}
                className="w-full text-left glass-card-hover p-4 flex items-center justify-between group"
              >
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="badge badge-primary">{s.subject_code}</span>
                    {s.semester && <span className="badge badge-muted">Sem {s.semester}</span>}
                    {s.credits && <span className="badge badge-muted">{s.credits} Cr</span>}
                  </div>
                  <p className="font-semibold text-white text-sm">{s.subject_name}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {s.unit_count} units · {s.topic_count} topics
                  </p>
                </div>
                <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-primary-400 transition-colors" />
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}

export default function Home() {
  return (
    <div className="min-h-screen pt-24 pb-16 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Hero */}
        <div className="text-center mb-14 animate-fade-in">
          <div className="inline-flex items-center gap-2 badge badge-primary mb-5 text-xs px-4 py-2">
            <Sparkles className="w-3.5 h-3.5" />
            AI-Powered Teaching Platform
          </div>
          <h1 className="text-5xl sm:text-6xl font-extrabold text-white tracking-tight leading-tight">
            Syllabus<span className="text-primary-400">AI</span>
          </h1>
          <p className="mt-4 text-lg text-slate-400 max-w-lg mx-auto font-medium">
            Manage your syllabus. Plan your classes.
            <br />
            <span className="text-slate-500 text-base">Upload a PDF → Search → Track → Teach with AI.</span>
          </p>
        </div>

        {/* Two-column layout */}
        <div className="grid md:grid-cols-2 gap-6">
          <UploadZone />
          <SearchSection />
        </div>

        {/* Feature row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-10">
          {[
            { icon: '📄', label: 'PDF Import', desc: 'Auto-extract subjects & units' },
            { icon: '🔍', label: 'Smart Search', desc: 'By name or subject code' },
            { icon: '✅', label: 'Track Progress', desc: 'Mark topics completed' },
            { icon: '🤖', label: 'RAG Chatbot', desc: 'Plan lessons with AI' },
          ].map((f) => (
            <div key={f.label} className="glass-card p-5 text-center hover:border-primary-500/20 transition-colors">
              <div className="text-2xl mb-2">{f.icon}</div>
              <p className="text-sm font-semibold text-white">{f.label}</p>
              <p className="text-xs text-slate-500 mt-1">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
