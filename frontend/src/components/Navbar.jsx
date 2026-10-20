import { useState, useRef, useEffect } from 'react'
import { NavLink, Link, useNavigate } from 'react-router-dom'
import { BookOpen, GraduationCap, Home, Sparkles, User, LogOut, ChevronDown, LogIn } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef(null)
  const navigate = useNavigate()

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const getInitials = (name) => {
    if (!name) return 'U'
    const parts = name.trim().split(/\s+/)
    if (parts.length >= 2) return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
    return name.substring(0, 2).toUpperCase()
  }

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-surface-900/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <NavLink to="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl bg-primary-600 flex items-center justify-center shadow-glow group-hover:scale-105 transition-transform">
            <BookOpen className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-lg text-white tracking-tight">
            Syllabus<span className="text-primary-400">AI</span>
          </span>
        </NavLink>

        {/* Nav links */}
        <div className="flex items-center gap-1 sm:gap-2">
          <NavLink
            to="/"
            end
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <Home className="w-4 h-4" />
            <span className="hidden sm:inline">Home</span>
          </NavLink>
          <NavLink
            to="/classes"
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <GraduationCap className="w-4 h-4" />
            <span className="hidden sm:inline">My Classes</span>
          </NavLink>
          <NavLink
            to="/ai"
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <Sparkles className="w-4 h-4" />
            <span className="hidden sm:inline">AI Assistant</span>
          </NavLink>

          {/* Auth Section */}
          <div className="ml-2 pl-2 border-l border-white/10 flex items-center">
            {isAuthenticated ? (
              <div className="relative" ref={dropdownRef}>
                <button
                  type="button"
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex items-center gap-2.5 p-1.5 sm:px-3 sm:py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition-colors text-left"
                >
                  <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-primary-600 to-accent-500 text-white flex items-center justify-center text-xs font-bold shadow-sm">
                    {getInitials(user?.full_name)}
                  </div>
                  <div className="hidden md:block">
                    <p className="text-xs font-semibold text-white leading-tight truncate max-w-[120px]">
                      {user?.full_name}
                    </p>
                    <p className="text-[10px] text-primary-400 uppercase tracking-wider font-semibold">
                      {user?.role || 'Faculty'}
                    </p>
                  </div>
                  <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden sm:block" />
                </button>

                {/* Dropdown Menu */}
                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-56 rounded-2xl bg-[#0f1124] border border-white/10 shadow-2xl p-2 z-50 animate-fade-in backdrop-blur-2xl">
                    <div className="px-3 py-2.5 border-b border-white/5 mb-1">
                      <p className="text-xs font-semibold text-white truncate">{user?.full_name}</p>
                      <p className="text-[11px] text-slate-400 truncate mt-0.5">{user?.email}</p>
                      {user?.department && (
                        <span className="badge badge-primary text-[10px] mt-1.5 inline-block">
                          {user.department}
                        </span>
                      )}
                    </div>

                    <Link
                      to="/classes"
                      onClick={() => setDropdownOpen(false)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
                    >
                      <GraduationCap className="w-4 h-4 text-primary-400" />
                      Manage Classes
                    </Link>

                    <button
                      type="button"
                      onClick={() => {
                        setDropdownOpen(false)
                        logout()
                        navigate('/')
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-xs text-rose-400 hover:bg-rose-500/10 rounded-xl transition-colors mt-1"
                    >
                      <LogOut className="w-4 h-4 text-rose-400" />
                      Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-1.5">
                <Link
                  to="/login"
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-primary-600 hover:bg-primary-500 rounded-xl shadow-glow transition-all"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  <span>Sign In</span>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
