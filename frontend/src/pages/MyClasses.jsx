import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  GraduationCap, Plus, Loader2, Trash2, BookOpen,
  ChevronRight, Users, BarChart3, X, Search, Sparkles, LogIn
} from 'lucide-react'
import { getClasses, createClass, deleteClass, getAllSubjects } from '../api'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'


function ProgressRing({ pct }) {
  const r = 24
  const circ = 2 * Math.PI * r
  const offset = circ - (pct / 100) * circ
  return (
    <svg width="64" height="64" viewBox="0 0 64 64" className="flex-shrink-0 -rotate-90">
      <circle cx="32" cy="32" r={r} fill="none" stroke="#222645" strokeWidth="6" />
      <circle
        cx="32" cy="32" r={r} fill="none"
        stroke="url(#prog-grad)" strokeWidth="6"
        strokeDasharray={circ} strokeDashoffset={offset}
        strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 0.7s ease-out' }}
      />
      <defs>
        <linearGradient id="prog-grad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#6172f5" />
          <stop offset="100%" stopColor="#ff5240" />
        </linearGradient>
      </defs>
    </svg>
  )
}

function ClassCard({ cls, onDelete }) {
  const navigate = useNavigate()
  const pct = cls.progress_percent || 0

  return (
    <div className="glass-card-hover p-6 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="badge badge-primary text-xs">{cls.subject_code}</span>
            {cls.semester && <span className="badge badge-muted text-xs">Sem {cls.semester}</span>}
          </div>
          <h3 className="font-bold text-white text-base leading-snug truncate">{cls.subject_name}</h3>
          <div className="flex flex-wrap gap-3 mt-2 text-xs text-slate-500">
            {cls.batch && <span className="flex items-center gap-1"><Users className="w-3 h-3" />{cls.batch}</span>}
            {cls.department && <span>{cls.department}</span>}
            {cls.section && <span>Section {cls.section}</span>}
          </div>
        </div>
        <div className="relative flex-shrink-0">
          <ProgressRing pct={pct} />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-xs font-bold text-white">{Math.round(pct)}%</span>
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div>
        <div className="flex justify-between text-xs text-slate-500 mb-1.5">
          <span>{cls.completed_topics} / {cls.total_topics} topics completed</span>
          <span>{pct.toFixed(0)}%</span>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        <button
          onClick={() => navigate(`/classes/${cls.id}`)}
          className="btn-secondary flex-1 justify-center text-xs py-2"
        >
          <BookOpen className="w-3.5 h-3.5" /> View Syllabus
        </button>
        <button
          onClick={() => navigate(`/classes/${cls.id}/plan`)}
          className="btn-primary flex-1 justify-center text-xs py-2"
        >
          <ChevronRight className="w-3.5 h-3.5" /> Plan Topics
        </button>
        <button
          onClick={() => onDelete(cls.id)}
          className="btn-ghost p-2 text-slate-600 hover:text-accent-400"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

function AddClassModal({ onClose, onAdded }) {
  const [subjects, setSubjects] = useState([])
  const [filtered, setFiltered] = useState([])
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState({ batch: '', department: '', section: '', semester: '' })
  const [loading, setLoading] = useState(false)
  const [loadingSubjects, setLoadingSubjects] = useState(true)

  useEffect(() => {
    getAllSubjects()
      .then((r) => { setSubjects(r.data.results); setFiltered(r.data.results) })
      .catch(() => toast.error('Failed to load subjects'))
      .finally(() => setLoadingSubjects(false))
  }, [])

  useEffect(() => {
    const q = search.toLowerCase()
    setFiltered(subjects.filter(s =>
      s.subject_name.toLowerCase().includes(q) || s.subject_code.toLowerCase().includes(q)
    ))
  }, [search, subjects])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!selected) return toast.error('Select a subject')
    setLoading(true)
    try {
      await createClass({ subject_id: selected.id, ...form })
      toast.success('Class added!')
      onAdded()
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add class')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative glass-card w-full max-w-lg p-8 animate-slide-up max-h-[90vh] overflow-y-auto">
        <button onClick={onClose} className="absolute top-4 right-4 btn-ghost p-2">
          <X className="w-4 h-4" />
        </button>
        <h3 className="text-xl font-bold text-white mb-6">Add a Class</h3>

        {/* Subject selector */}
        <div className="mb-5">
          <label className="input-label">Subject</label>
          <div className="relative mb-2">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              className="input-field pl-10"
              placeholder="Search subjects…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="max-h-48 overflow-y-auto space-y-1 pr-1">
            {loadingSubjects ? (
              <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin text-primary-400" /></div>
            ) : filtered.length === 0 ? (
              <p className="text-center py-4 text-slate-500 text-sm">No subjects found. Upload a PDF first.</p>
            ) : (
              filtered.map(s => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => { setSelected(s); setForm(f => ({ ...f, semester: s.semester || '' })) }}
                  className={`w-full text-left px-3 py-2.5 rounded-xl text-sm transition-all ${
                    selected?.id === s.id
                      ? 'bg-primary-600/25 border border-primary-500/50 text-white'
                      : 'hover:bg-white/5 text-slate-400'
                  }`}
                >
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="font-semibold font-mono text-primary-400">{s.subject_code}</span>
                    {s.regulation && <span className="badge badge-indigo text-[10px] py-0 px-1.5">{s.regulation}</span>}
                    {s.semester && (
                      <span className="badge badge-muted text-[10px] py-0 px-1.5">
                        {s.semester.toLowerCase() === 'elective' ? 'Elective' : `Sem ${s.semester}`}
                      </span>
                    )}
                    <span className="text-white text-xs truncate">{s.subject_name}</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {[
            { key: 'batch', label: 'Batch', placeholder: '2025–2029' },
            { key: 'department', label: 'Department', placeholder: 'Information Technology' },
            { key: 'section', label: 'Section', placeholder: 'A' },
            { key: 'semester', label: 'Semester', placeholder: 'V' },
          ].map(({ key, label, placeholder }) => (
            <div key={key}>
              <label className="input-label">{label}</label>
              <input
                className="input-field"
                placeholder={placeholder}
                value={form[key]}
                onChange={e => setForm({ ...form, [key]: e.target.value })}
              />
            </div>
          ))}
          <div className="flex gap-3 pt-2">
            <button type="button" className="btn-secondary flex-1 justify-center" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary flex-1 justify-center" disabled={loading || !selected}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Add Class
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function MyClasses() {
  const { user, isAuthenticated } = useAuth()
  const [classes, setClasses] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)

  const load = () => {
    setLoading(true)
    getClasses()
      .then(r => setClasses(r.data))
      .catch(() => toast.error('Failed to load classes'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [isAuthenticated])

  const handleDelete = async (id) => {
    if (!confirm('Remove this class?')) return
    try {
      await deleteClass(id)
      toast.success('Class removed')
      load()
    } catch {
      toast.error('Failed to delete class')
    }
  }

  return (
    <div className="min-h-screen pt-24 pb-16 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Auth prompt if not logged in */}
        {!isAuthenticated && (
          <div className="mb-6 p-3.5 rounded-2xl glass-card border border-white/10 flex items-center justify-between gap-3 animate-fade-in">
            <div className="flex items-center gap-2.5">
              <Sparkles className="w-4 h-4 text-primary-400" />
              <p className="text-xs text-slate-300">
                You are browsing as guest. Sign in to link newly added classes to your faculty account.
              </p>
            </div>
            <Link
              to="/login"
              className="text-xs font-semibold text-primary-400 hover:text-primary-300 flex items-center gap-1 whitespace-nowrap"
            >
              <LogIn className="w-3.5 h-3.5" /> Sign In
            </Link>
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="section-title flex items-center gap-3">
              <GraduationCap className="w-7 h-7 text-primary-400" />
              {isAuthenticated ? `${user.full_name}'s Classes` : 'My Classes'}
            </h1>
            <p className="section-subtitle mt-1">
              {isAuthenticated
                ? `Faculty Portfolio · ${user.department || 'Academic Department'}`
                : 'Track your subjects, sections & teaching progress'}
            </p>
          </div>
          <button onClick={() => setShowModal(true)} className="btn-primary">
            <Plus className="w-4 h-4" /> Add Class
          </button>
        </div>


        {/* Stats row */}
        {classes.length > 0 && (
          <div className="grid grid-cols-3 gap-4 mb-8">
            {[
              { label: 'Active Classes', value: classes.length, icon: GraduationCap, color: 'text-primary-400' },
              { label: 'Total Topics', value: classes.reduce((a, c) => a + c.total_topics, 0), icon: BookOpen, color: 'text-accent-400' },
              { label: 'Avg Progress', value: `${(classes.reduce((a, c) => a + c.progress_percent, 0) / classes.length).toFixed(0)}%`, icon: BarChart3, color: 'text-emerald-400' },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="glass-card p-5 flex items-center gap-4">
                <div className={`w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center flex-shrink-0 ${color}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{value}</p>
                  <p className="text-xs text-slate-500">{label}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Class grid */}
        {loading ? (
          <div className="grid md:grid-cols-2 gap-5">
            {[1, 2].map(i => <div key={i} className="h-64 skeleton rounded-2xl" />)}
          </div>
        ) : classes.length === 0 ? (
          <div className="glass-card p-16 text-center">
            <GraduationCap className="w-14 h-14 text-slate-700 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">No classes yet</h3>
            <p className="text-slate-500 text-sm mb-6">Add the subjects you're currently teaching to track progress.</p>
            <button onClick={() => setShowModal(true)} className="btn-primary mx-auto">
              <Plus className="w-4 h-4" /> Add Your First Class
            </button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-5">
            {classes.map(cls => (
              <ClassCard key={cls.id} cls={cls} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <AddClassModal onClose={() => setShowModal(false)} onAdded={load} />
      )}
    </div>
  )
}
