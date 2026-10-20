import { useState, useCallback, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Upload,
  Search,
  FileText,
  Loader2,
  CheckCircle2,
  AlertCircle,
  X,
  ChevronRight,
  Sparkles,
  Layers,
  GraduationCap,
  ArrowRight,
  Filter,
} from 'lucide-react'
import { uploadPDF, searchSubjects, getSemesters } from '../api'
import { useAuth } from '../context/AuthContext'
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
    <div className="glass-card p-7 sm:p-8 animate-fade-in flex flex-col justify-between">
      <div>
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-primary-600/20 border border-primary-500/30 flex items-center justify-center">
            <Upload className="w-5 h-5 text-primary-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Upload Syllabus PDF</h2>
            <p className="text-xs text-slate-400">Extracts all subjects, units & topics automatically</p>
          </div>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={`relative border-2 border-dashed rounded-xl p-8 sm:p-10 text-center transition-all duration-200 cursor-pointer ${
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
                onClick={(e) => {
                  e.stopPropagation()
                  setFile(null)
                  setResult(null)
                }}
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
                <span key={s.id} className="badge badge-success text-xs">
                  {s.subject_code} — {s.subject_name}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <button
        className="btn-primary w-full mt-6 justify-center"
        onClick={handleUpload}
        disabled={!file || uploading}
      >
        {uploading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" /> Processing…
          </>
        ) : (
          <>
            <Upload className="w-4 h-4" /> Upload & Extract
          </>
        )}
      </button>
    </div>
  )
}

function SearchSection() {
  const [query, setQuery] = useState('')
  const [selectedSemester, setSelectedSemester] = useState(null)
  const [availableSemesters, setAvailableSemesters] = useState([])
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const navigate = useNavigate()

  // Fetch available semesters on mount
  useEffect(() => {
    const loadSemesters = async () => {
      try {
        const res = await getSemesters()
        if (res.data && res.data.length > 0) {
          setAvailableSemesters(res.data)
        } else {
          // Fallback semesters 1..8
          setAvailableSemesters([1, 2, 3, 4, 5, 6, 7, 8].map((s) => ({
            semester: String(s),
            display_name: `Semester ${s}`,
            count: 0,
          })))
        }
      } catch {
        // Fallback default semesters
        setAvailableSemesters([1, 2, 3, 4, 5, 6, 7, 8].map((s) => ({
          semester: String(s),
          display_name: `Semester ${s}`,
          count: 0,
        })))
      }
    }
    loadSemesters()
  }, [])

  const executeSearch = async (searchTerm, semFilter = null) => {
    setLoading(true)
    try {
      const res = await searchSubjects(searchTerm, semFilter)
      setResults(res.data)
      if (res.data.total === 0) {
        toast('No subjects found', { icon: '🔍' })
      }
    } catch {
      toast.error('Search failed. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const handleSearchSubmit = (e) => {
    e?.preventDefault()
    if (!query.trim() && !selectedSemester) return
    executeSearch(query, selectedSemester)
  }

  const handleSemesterPillClick = (semValue) => {
    if (selectedSemester === semValue) {
      // Toggle off
      setSelectedSemester(null)
      setQuery('')
      executeSearch('', null)
    } else {
      setSelectedSemester(semValue)
      const label = semValue.toLowerCase() === 'elective' ? 'Electives' : `Sem ${semValue}`
      setQuery(label)
      executeSearch(label, semValue)
    }
  }

  const handleClearFilters = () => {
    setQuery('')
    setSelectedSemester(null)
    setResults(null)
  }

  return (
    <div className="glass-card p-7 sm:p-8 animate-fade-in" style={{ animationDelay: '0.1s' }}>
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-accent-600/20 border border-accent-500/30 flex items-center justify-center">
            <Search className="w-5 h-5 text-accent-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Search Subjects</h2>
            <p className="text-xs text-slate-400">Search by code, subject name, semester (e.g. "sem 4"), or regulation</p>
          </div>
        </div>

        {(query || selectedSemester || results) && (
          <button
            onClick={handleClearFilters}
            className="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition-colors px-2 py-1 rounded-lg bg-white/5"
          >
            <X className="w-3 h-3" /> Clear
          </button>
        )}
      </div>

      {/* Search Input Form */}
      <form onSubmit={handleSearchSubmit} className="flex gap-2 sm:gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
          <input
            id="search-input"
            className="input-field pl-10"
            placeholder="Type subject code, name, 'sem 4', or regulation…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <button
          className="btn-accent px-4 sm:px-5"
          type="submit"
          disabled={loading || (!query.trim() && !selectedSemester)}
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          <span className="hidden sm:inline">Search</span>
        </button>
      </form>

      {/* Semester Quick Filter Pills */}
      <div className="mt-4">
        <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-2">
          <Filter className="w-3.5 h-3.5 text-primary-400" />
          <span className="font-semibold text-slate-300">Quick Semester Filter:</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {availableSemesters.map((s) => {
            const isElective = s.semester.toLowerCase() === 'elective'
            const isSelected =
              selectedSemester === s.semester ||
              (isElective
                ? query.toLowerCase().includes('elec')
                : query.toLowerCase().includes(`sem ${s.semester}`))
            const pillLabel = isElective ? 'Electives' : `Sem ${s.semester}`

            return (
              <button
                key={s.semester}
                type="button"
                onClick={() => handleSemesterPillClick(s.semester)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                  isSelected
                    ? 'bg-primary-600 text-white shadow-glow border border-primary-400/50'
                    : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 border border-white/5'
                }`}
              >
                <span>{pillLabel}</span>
                {s.count > 0 && (
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                      isSelected ? 'bg-white/20 text-white' : 'bg-white/10 text-slate-400'
                    }`}
                  >
                    {s.count}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Results Header if detected semester */}
      {results && results.detected_semester && (
        <div className="mt-4 p-2.5 rounded-xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-between text-xs animate-fade-in">
          <div className="flex items-center gap-2">
            <span className="badge badge-primary text-xs">
              {results.detected_semester.toLowerCase() === 'elective'
                ? 'Electives'
                : `Semester ${results.detected_semester}`}
            </span>
            <span className="text-slate-300">
              Found <strong>{results.total}</strong> subject(s){' '}
              {results.detected_semester.toLowerCase() === 'elective'
                ? 'in Electives'
                : `in Semester ${results.detected_semester}`}
            </span>
          </div>
        </div>
      )}

      {/* Results List */}
      {results && (
        <div className="mt-4 space-y-2.5 max-h-[380px] overflow-y-auto pr-1 animate-slide-up custom-scrollbar">
          {results.total === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm font-medium">No subjects found for "{results.query || (selectedSemester ? `Sem ${selectedSemester}` : '')}"</p>
              <p className="text-xs mt-1">Try another search keyword, subject code, or semester</p>
            </div>
          ) : (
            results.results.map((s) => (
              <button
                key={s.id}
                onClick={() => navigate(`/subjects/${s.id}`)}
                className="w-full text-left glass-card-hover p-3.5 flex items-center justify-between group rounded-xl"
              >
                <div>
                  <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                    <span className="badge badge-primary text-xs font-mono font-bold">{s.subject_code}</span>
                    <span className="badge badge-indigo text-xs font-semibold">{s.regulation || 'Regulation 2023'}</span>
                    {s.semester && (
                      <span className="badge badge-accent text-xs">
                        {s.semester.toLowerCase() === 'elective' ? 'Elective' : `Sem ${s.semester}`}
                      </span>
                    )}
                    {s.credits && <span className="badge badge-muted text-xs">{s.credits} Cr</span>}
                    {s.course_type && (
                      <span className="text-[10px] text-slate-400 bg-white/5 border border-white/5 px-2 py-0.5 rounded-md">
                        {s.course_type}
                      </span>
                    )}
                  </div>
                  <p className="font-semibold text-white text-sm line-clamp-1">{s.subject_name}</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    {s.unit_count} units · {s.topic_count} topics
                  </p>
                </div>
                <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-primary-400 transition-colors flex-shrink-0 ml-2" />
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}

export default function Home() {
  const { user, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen pt-24 pb-16 px-4">
      <div className="max-w-5xl mx-auto">
        {/* User personalized banner if logged in */}
        {isAuthenticated ? (
          <div className="mb-8 p-4 rounded-2xl glass-card border border-primary-500/20 bg-primary-950/20 flex flex-col sm:flex-row items-center justify-between gap-4 animate-fade-in">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary-600/30 border border-primary-500/30 flex items-center justify-center text-primary-300 font-bold">
                <GraduationCap className="w-5 h-5 text-primary-400" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-white">
                    Welcome back, {user?.full_name}!
                  </h3>
                  <span className="badge badge-primary text-[10px] uppercase">
                    {user?.role || 'Faculty'}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  {user?.department ? `${user.department} Department · ` : ''}
                  Ready to manage semesters and class progress?
                </p>
              </div>
            </div>
            <Link
              to="/classes"
              className="btn-primary text-xs px-4 py-2 flex items-center gap-1.5 whitespace-nowrap"
            >
              <span>Go to My Classes</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        ) : (
          <div className="mb-8 p-3.5 rounded-2xl glass-card border border-white/10 flex items-center justify-between gap-3 animate-fade-in">
            <div className="flex items-center gap-2.5">
              <Sparkles className="w-4 h-4 text-primary-400" />
              <p className="text-xs text-slate-300">
                Are you a faculty member? Sign in to save your assigned classes and topic progress.
              </p>
            </div>
            <Link
              to="/login"
              className="text-xs font-semibold text-primary-400 hover:text-primary-300 whitespace-nowrap flex items-center gap-1"
            >
              Sign In <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        )}

        {/* Hero */}
        <div className="text-center mb-12 animate-fade-in">
          <div className="inline-flex items-center gap-2 badge badge-primary mb-4 text-xs px-4 py-2">
            <Sparkles className="w-3.5 h-3.5" />
            AI-Powered Teaching Platform
          </div>
          <h1 className="text-4xl sm:text-6xl font-extrabold text-white tracking-tight leading-tight">
            Syllabus<span className="text-primary-400">AI</span>
          </h1>
          <p className="mt-4 text-base sm:text-lg text-slate-400 max-w-xl mx-auto font-medium">
            Search subjects across all semesters (Sem 1 to Sem 8), track syllabus completion, and generate AI lesson plans.
          </p>
        </div>

        {/* Two-column layout */}
        <div className="grid md:grid-cols-2 gap-6 items-start">
          <SearchSection />
          <UploadZone />
        </div>

        {/* Feature row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-10">
          {[
            { icon: '🔍', label: 'Semester Search', desc: 'Search "sem 6", "sem 3", etc.' },
            { icon: '📄', label: 'PDF Import', desc: 'Auto-extract subjects & units' },
            { icon: '🔒', label: 'Faculty Auth', desc: 'Secure teacher login & classes' },
            { icon: '🤖', label: 'RAG Chatbot', desc: 'AI lesson plans & queries' },
          ].map((f) => (
            <div
              key={f.label}
              className="glass-card p-5 text-center hover:border-primary-500/20 transition-colors"
            >
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
