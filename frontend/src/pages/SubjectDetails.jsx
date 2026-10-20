import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, BookOpen, Clock, Award, Layers,
  Target, CheckCircle, Plus, Loader2, ChevronDown, ChevronRight
} from 'lucide-react'
import { getSubject, getClasses, createClass } from '../api'
import toast from 'react-hot-toast'

function MetaBadge({ label, value }) {
  if (!value) return null
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</span>
      <span className="text-sm font-semibold text-white">{value}</span>
    </div>
  )
}

function UnitAccordion({ unit }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-white/2 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary-600/20 border border-primary-500/30 flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-bold text-primary-400">{unit.unit_number}</span>
          </div>
          <div className="text-left">
            <p className="font-bold text-white text-sm">UNIT {unit.unit_number}</p>
            <p className="text-primary-300 text-xs font-medium mt-0.5">{unit.unit_title}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="badge badge-muted text-xs">{unit.topics?.length || 0} topics</span>
          {open ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
        </div>
      </button>
      {open && unit.topics?.length > 0 && (
        <div className="border-t border-white/5 px-6 py-4">
          <ol className="space-y-2">
            {unit.topics.map((t) => (
              <li key={t.id} className="flex items-start gap-3 text-sm">
                <span className="text-slate-600 font-mono text-xs mt-0.5 w-5 flex-shrink-0">{t.topic_order}.</span>
                <span className="text-slate-300">{t.topic_name}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}

function AddClassModal({ subject, onClose, onAdded }) {
  const [form, setForm] = useState({
    batch: '',
    department: '',
    section: '',
    semester: subject?.semester || '',
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await createClass({ subject_id: subject.id, ...form })
      toast.success('Class added to My Classes!')
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
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative glass-card w-full max-w-md p-8 animate-slide-up">
        <h3 className="text-xl font-bold text-white mb-1">Add to My Classes</h3>
        <p className="text-sm text-slate-500 mb-6">{subject?.subject_name}</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          {[
            { key: 'batch', label: 'Batch (e.g. 2025–2029)', placeholder: '2025–2029' },
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
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              />
            </div>
          ))}
          <div className="flex gap-3 pt-2">
            <button type="button" className="btn-secondary flex-1 justify-center" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary flex-1 justify-center" disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Add Class
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function SubjectDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [subject, setSubject] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)

  useEffect(() => {
    getSubject(id)
      .then((r) => setSubject(r.data))
      .catch(() => toast.error('Subject not found'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="min-h-screen pt-24 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
      </div>
    )
  }

  if (!subject) {
    return (
      <div className="min-h-screen pt-24 flex items-center justify-center text-slate-500">
        Subject not found.
      </div>
    )
  }

  const totalTopics = subject.units?.reduce((a, u) => a + (u.topics?.length || 0), 0) || 0
  const ltp = [subject.lecture_hours, subject.tutorial_hours, subject.practical_hours]
    .map((v) => (v ?? '-'))
    .join(' / ')

  return (
    <div className="min-h-screen pt-24 pb-16 px-4">
      <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
        {/* Back */}
        <button onClick={() => navigate(-1)} className="btn-ghost -ml-2">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        {/* Header card */}
        <div className="glass-card p-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-3">
                <span className="badge badge-primary text-sm px-3 py-1 font-mono font-bold">{subject.subject_code}</span>
                <span className="badge badge-indigo text-sm px-3 py-1 font-semibold">{subject.regulation || 'Regulation 2023'}</span>
                {subject.semester && (
                  <span className="badge badge-muted">
                    {subject.semester.toLowerCase() === 'elective' ? 'Elective' : `Semester ${subject.semester}`}
                  </span>
                )}
                {subject.course_type && (
                  <span className="badge badge-accent">{subject.course_type}</span>
                )}
              </div>
              <h1 className="text-3xl font-extrabold text-white tracking-tight">{subject.subject_name}</h1>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="btn-primary"
            >
              <Plus className="w-4 h-4" /> Add to My Classes
            </button>
          </div>

          {/* Meta grid */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-6 mt-8 pt-6 border-t border-white/5">
            <MetaBadge label="Regulation" value={subject.regulation || 'Regulation 2023'} />
            <MetaBadge label="Credits" value={subject.credits} />
            <MetaBadge label="L / T / P" value={ltp} />
            <MetaBadge
              label="Units"
              value={`${subject.units?.length || 0} units`}
            />
            <MetaBadge label="Total Topics" value={`${totalTopics} topics`} />
          </div>
        </div>

        {/* Objectives */}
        {subject.course_objectives?.length > 0 && (
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Target className="w-5 h-5 text-primary-400" />
              <h2 className="text-base font-bold text-white uppercase tracking-wider">Course Objectives</h2>
            </div>
            <ul className="space-y-2">
              {subject.course_objectives.map((obj, i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-slate-300">
                  <span className="text-primary-500 mt-1 flex-shrink-0">•</span>
                  {obj}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Outcomes */}
        {subject.course_outcomes?.length > 0 && (
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle className="w-5 h-5 text-emerald-400" />
              <h2 className="text-base font-bold text-white uppercase tracking-wider">Course Outcomes</h2>
            </div>
            <div className="space-y-3">
              {subject.course_outcomes.map((co, i) => (
                <div key={i} className="flex items-start gap-4">
                  <span className="badge badge-success flex-shrink-0">{co.code || `CO${i + 1}`}</span>
                  <span className="text-sm text-slate-300">{co.description}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Syllabus units */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Layers className="w-5 h-5 text-primary-400" />
            <h2 className="text-base font-bold text-white uppercase tracking-wider">Syllabus</h2>
          </div>
          <div className="space-y-3">
            {subject.units?.map((unit) => (
              <UnitAccordion key={unit.id} unit={unit} />
            ))}
            {(!subject.units || subject.units.length === 0) && (
              <div className="glass-card p-10 text-center text-slate-500">
                No units extracted. The PDF may need manual structure.
              </div>
            )}
          </div>
        </div>
      </div>

      {showAddModal && (
        <AddClassModal
          subject={subject}
          onClose={() => setShowAddModal(false)}
          onAdded={() => {}}
        />
      )}
    </div>
  )
}
