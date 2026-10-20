import { createContext, useContext, useState, useEffect } from 'react'
import { getMe, loginUser, registerUser, demoLoginUser } from '../api'
import toast from 'react-hot-toast'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('syllabusai_token'))
  const [loading, setLoading] = useState(true)

  // Validate existing token on mount
  useEffect(() => {
    const fetchUser = async () => {
      const storedToken = localStorage.getItem('syllabusai_token')
      if (!storedToken) {
        setLoading(false)
        return
      }
      try {
        const res = await getMe()
        setUser(res.data)
      } catch {
        // Token invalid or expired
        localStorage.removeItem('syllabusai_token')
        setToken(null)
        setUser(null)
      } finally {
        setLoading(false)
      }
    }
    fetchUser()
  }, [])

  const login = async (email, password) => {
    try {
      const res = await loginUser({ email, password })
      const { access_token, user: userData } = res.data
      localStorage.setItem('syllabusai_token', access_token)
      setToken(access_token)
      setUser(userData)
      toast.success(`Welcome back, ${userData.full_name}!`)
      return { success: true }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Login failed. Please check your credentials.'
      toast.error(msg)
      return { success: false, error: msg }
    }
  }

  const register = async (formData) => {
    try {
      const res = await registerUser(formData)
      const { access_token, user: userData } = res.data
      localStorage.setItem('syllabusai_token', access_token)
      setToken(access_token)
      setUser(userData)
      toast.success(`Account created! Welcome, ${userData.full_name}.`)
      return { success: true }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Registration failed.'
      toast.error(msg)
      return { success: false, error: msg }
    }
  }

  const demoLogin = async () => {
    try {
      const res = await demoLoginUser()
      const { access_token, user: userData } = res.data
      localStorage.setItem('syllabusai_token', access_token)
      setToken(access_token)
      setUser(userData)
      toast.success(`Signed in as ${userData.full_name} (Demo Faculty)`)
      return { success: true }
    } catch {
      toast.error('Demo login failed.')
      return { success: false }
    }
  }

  const logout = () => {
    localStorage.removeItem('syllabusai_token')
    setToken(null)
    setUser(null)
    toast.success('Signed out successfully.')
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        loading,
        login,
        register,
        demoLogin,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}
