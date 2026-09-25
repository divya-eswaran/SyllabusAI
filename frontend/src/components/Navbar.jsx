import { NavLink } from 'react-router-dom'
import { BookOpen, GraduationCap, Home, Sparkles } from 'lucide-react'

export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-surface-900/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
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
        <div className="flex items-center gap-1">
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
        </div>
      </div>
    </nav>
  )
}
