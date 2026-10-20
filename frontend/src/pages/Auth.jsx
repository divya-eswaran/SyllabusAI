import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import {
  Lock,
  Mail,
  User,
  GraduationCap,
  Building,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  Loader2,
  CheckCircle2,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Auth({ initialMode = 'login' }) {
  const [isLogin, setIsLogin] = useState(initialMode === 'login')
  const [loading, setLoading] = useState(false)
  const [demoLoading, setDemoLoading] = useState(false)

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    department: 'Information Technology',
    role: 'teacher',
  })

  const { login, register, demoLogin } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from?.pathname || '/'

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    let res
    if (isLogin) {
      res = await login(formData.email, formData.password)
    } else {
      res = await register(formData)
    }
    setLoading(false)
    if (res.success) {
      navigate(from, { replace: true })
    }
  }

  const handleDemoLogin = async () => {
    setDemoLoading(true)
    const res = await demoLogin()
    setDemoLoading(false)
    if (res.success) {
      navigate(from, { replace: true })
    }
  }

  return (
    <div className="min-h-screen pt-28 pb-16 px-4 flex items-center justify-center relative overflow-hidden">
      {/* Background ambient glows */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-primary-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-1/4 w-[400px] h-[400px] bg-accent-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10 animate-fade-in">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 badge badge-primary mb-3 text-xs px-3 py-1.5">
            <ShieldCheck className="w-3.5 h-3.5" />
            Secure Authentication
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            {isLogin ? 'Sign in to ' : 'Create your '}
            <span className="text-primary-400">SyllabusAI</span>
          </h1>
          <p className="text-sm text-slate-400 mt-2">
            {isLogin
              ? 'Access your course plans, syllabus tracker, and AI assistant.'
              : 'Join as a teacher or faculty member to manage curriculum seamlessly.'}
          </p>
        </div>

        {/* Card */}
        <div className="glass-card p-7 sm:p-8 shadow-2xl border border-white/10 backdrop-blur-2xl">
          {/* Tabs */}
          <div className="flex rounded-xl bg-white/5 p-1 mb-6 border border-white/5">
            <button
              type="button"
              onClick={() => setIsLogin(true)}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                isLogin
                  ? 'bg-primary-600 text-white shadow-glow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => setIsLogin(false)}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                !isLogin
                  ? 'bg-primary-600 text-white shadow-glow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Full Name
                  </label>
                  <div className="relative">
                    <User className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      type="text"
                      required
                      placeholder="Dr. Ramesh Kumar"
                      value={formData.full_name}
                      onChange={(e) =>
                        setFormData({ ...formData, full_name: e.target.value })
                      }
                      className="input-field pl-10"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Department
                  </label>
                  <div className="relative">
                    <Building className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      type="text"
                      placeholder="Information Technology"
                      value={formData.department}
                      onChange={(e) =>
                        setFormData({ ...formData, department: e.target.value })
                      }
                      className="input-field pl-10"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Role
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { id: 'teacher', label: 'Faculty / Teacher' },
                      { id: 'student', label: 'Student' },
                    ].map((r) => (
                      <button
                        key={r.id}
                        type="button"
                        onClick={() => setFormData({ ...formData, role: r.id })}
                        className={`py-2 px-3 rounded-lg border text-xs font-medium transition-all text-center ${
                          formData.role === r.id
                            ? 'border-primary-500 bg-primary-600/20 text-white'
                            : 'border-white/10 bg-white/5 text-slate-400 hover:border-white/20'
                        }`}
                      >
                        {r.label}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="email"
                  required
                  placeholder="faculty@annauniv.edu"
                  value={formData.email}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  className="input-field pl-10"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="password"
                  required
                  minLength={6}
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={(e) =>
                    setFormData({ ...formData, password: e.target.value })
                  }
                  className="input-field pl-10"
                />
              </div>
              {!isLogin && (
                <p className="text-[11px] text-slate-500 mt-1">
                  Must be at least 6 characters
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full justify-center py-2.5 mt-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {isLogin ? 'Signing In…' : 'Creating Account…'}
                </>
              ) : (
                <>
                  <span>{isLogin ? 'Sign In' : 'Create Account'}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Login Option */}
          <div className="mt-6 pt-5 border-t border-white/10">
            <p className="text-center text-xs text-slate-400 mb-3">
              Testing the application?
            </p>
            <button
              type="button"
              disabled={demoLoading}
              onClick={handleDemoLogin}
              className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-xl border border-primary-500/30 bg-primary-500/10 hover:bg-primary-500/20 text-primary-300 text-xs font-semibold transition-all group"
            >
              {demoLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4 text-primary-400 group-hover:scale-110 transition-transform" />
              )}
              Instant Demo Faculty Login (Dr. Ramesh Kumar)
            </button>
          </div>
        </div>

        {/* Back link */}
        <div className="text-center mt-6">
          <Link
            to="/"
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            ← Back to SyllabusAI Home
          </Link>
        </div>
      </div>
    </div>
  )
}
