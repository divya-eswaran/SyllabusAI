import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, CheckCircle2, Circle, Loader2,
  Sparkles, BookOpen, BarChart3, ChevronRight
} from 'lucide-react'
import { getClass, getClassProgress, toggleTopicProgress } from '../api'
import toast from 'react-hot-toast'

function TopicRow({ item, onToggle, loading }) {
  return (
    <button
      onClick={() => onToggle(item.topic_id, !item.is_completed)}
      disabled={loading}
      className={`topic-item w-full text-left ${item.is_completed ? 'opacity-80' : ''}`}
    >
      <div className={`topic-checkbox ${item.is_completed ? 'completed' : 'pending'}`}>
        {item.is_completed && (
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 12 12" stroke="currentColor" strokeWidth="2.5">
            <polyline points="2,6 5,9 10,3" />
          </svg>
        )}
      </div>
      <span className={`text-sm flex-1 ${item.is_completed ? 'text-slate-500 line-through' : 'text-slate-200'}`}>
        {item.topic_name}
      </span>
      {item.is_completed && (
        <span className="badge badge-success text-xs flex-shrink-0">Done</span>
      )}
    </button>
  )
}

export default function TeacherWorkspace() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [cls, setCls] = useState(null)
  const [progress, setProgress] = useState([])
  const [loading, setLoading] = useState(true)
  const [toggling, setToggling] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const [clsRes, progRes] = await Promise.all([getClass(id), getClassProgress(id)])
      setCls(clsRes.data)
      setProgress(progRes.data)
    } catch {
      toast.error('Failed to load class data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  const handleToggle = async (topicId, isCompleted) => {
    setToggling(topicId)
    try {
      const res = await toggleTopicProgress(id, topicId, isCompleted)
      setProgress(prev =>
        prev.map(p => p.topic_id === topicId ? { ...p, is_completed: res.data.is_completed, completed_at: res.data.completed_at } : p)
      )
    } catch {
      toast.error('Failed to update topic')
    } finally {
      setToggling(null)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen pt-24 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
      </div>
    )
  }

  if (!cls) return <div className="min-h-screen pt-24 text-center text-slate-500">Class not found.</div>

  // Group by unit
  const byUnit = {}
  for (const item of progress) {
    const key = item.unit_id
    if (!byUnit[key]) byUnit[key] = { unit_number: item.unit_number, unit_title: item.unit_title, topics: [] }
    byUnit[key].topics.push(item)
  }
  const units = Object.values(byUnit).sort((a, b) => a.unit_number - b.unit_number)

  const completed = progress.filter(p => p.is_completed).length
  const total = progress.length
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0

  // Upcoming = first N incomplete topics in order
  const upcoming = progress.filter(p => !p.is_completed).slice(0, 6)

  return (
    <div className="min-h-screen pt-24 pb-16 px-4">
      <div className="max-w-5xl mx-auto space-y-6 animate-fade-in">
        <button onClick={() => navigate('/classes')} className="btn-ghost -ml-2">
          <ArrowLeft className="w-4 h-4" /> My Classes
        </button>

        {/* Class header */}
        <div className="glass-card p-7">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex flex-wrap gap-2 mb-2">
                <span className="badge badge-primary">{cls.subject_code}</span>
                {cls.semester && <span className="badge badge-muted">Sem {cls.semester}</span>}
                {cls.batch && <span className="badge badge-muted">{cls.batch}</span>}
                {cls.section && <span className="badge badge-muted">Section {cls.section}</span>}
              </div>
              <h1 className="text-2xl font-extrabold text-white">{cls.subject_name}</h1>
              {cls.department && <p className="text-sm text-slate-500 mt-1">{cls.department}</p>}
            </div>
            <div className="text-right">
              <p className="text-4xl font-black text-white">{pct}%</p>
              <p className="text-xs text-slate-500">{completed} / {total} topics</p>
            </div>
          </div>
          <div className="mt-5">
            <div className="progress-bar h-3">
              <div className="progress-fill" style={{ width: `${pct}%` }} />
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Syllabus tracker */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary-400" />
              <h2 className="text-base font-bold text-white">Interactive Syllabus</h2>
              <span className="text-xs text-slate-500 ml-1">— Click to mark complete</span>
            </div>

            {units.map((unit) => {
              const unitCompleted = unit.topics.filter(t => t.is_completed).length
              const unitTotal = unit.topics.length
              const unitPct = unitTotal > 0 ? Math.round((unitCompleted / unitTotal) * 100) : 0

              return (
                <div key={unit.unit_number} className="glass-card overflow-hidden">
                  <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-primary-600/20 border border-primary-500/30 flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-bold text-primary-400">{unit.unit_number}</span>
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-slate-500">UNIT {unit.unit_number}</p>
                        <p className="text-sm font-bold text-white">{unit.unit_title}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">{unitCompleted}/{unitTotal}</span>
                      <div className="w-16 progress-bar h-1.5">
                        <div className="progress-fill h-full" style={{ width: `${unitPct}%` }} />
                      </div>
                    </div>
                  </div>
                  <div className="p-2">
                    {unit.topics.sort((a, b) => a.topic_order - b.topic_order).map((t) => (
                      <TopicRow
                        key={t.topic_id}
                        item={t}
                        onToggle={handleToggle}
                        loading={toggling === t.topic_id}
                      />
                    ))}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Sidebar — upcoming & AI */}
          <div className="space-y-5">
            {/* Upcoming topics */}
            <div className="glass-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-4 h-4 text-accent-400" />
                <h3 className="text-sm font-bold text-white">Upcoming Topics</h3>
              </div>
              {upcoming.length === 0 ? (
                <div className="text-center py-6">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                  <p className="text-sm text-slate-400 font-semibold">All topics completed! 🎉</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {upcoming.map((t, i) => (
                    <div key={t.topic_id} className="flex items-start gap-3 py-2.5 px-3 rounded-xl hover:bg-white/3 transition-colors">
                      <span className="text-xs text-primary-500 font-bold mt-0.5 w-4 flex-shrink-0">{i + 1}</span>
                      <span className="text-xs text-slate-300 leading-snug">{t.topic_name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Plan with AI */}
            {upcoming.length > 0 && (
              <div className="glass-card p-5 border border-primary-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="w-4 h-4 text-primary-400" />
                  <h3 className="text-sm font-bold text-white">Plan with AI</h3>
                </div>
                <p className="text-xs text-slate-500 mb-4">
                  Select an upcoming topic and let the AI help you plan a lesson.
                </p>
                <div className="space-y-2">
                  {upcoming.slice(0, 4).map((t) => (
                    <button
                      key={t.topic_id}
                      onClick={() => navigate(`/ai?classId=${id}&topicId=${t.topic_id}&topicName=${encodeURIComponent(t.topic_name)}`)}
                      className="w-full text-left flex items-center gap-2 px-3 py-2.5 rounded-xl bg-white/3 hover:bg-primary-600/15 border border-white/5 hover:border-primary-500/30 transition-all text-xs text-slate-300 group"
                    >
                      <Sparkles className="w-3 h-3 text-primary-500 flex-shrink-0 group-hover:text-primary-300" />
                      <span className="truncate">{t.topic_name}</span>
                      <ChevronRight className="w-3 h-3 text-slate-600 ml-auto flex-shrink-0" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
