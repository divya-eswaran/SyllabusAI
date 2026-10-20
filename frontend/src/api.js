import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 120000,
})

// Attach JWT token automatically to every request if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('syllabusai_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const loginUser = (data) => api.post('/api/auth/login', data)
export const registerUser = (data) => api.post('/api/auth/register', data)
export const getMe = () => api.get('/api/auth/me')
export const demoLoginUser = () => api.post('/api/auth/demo-login')

// ─── PDF ──────────────────────────────────────────────────────────────────────
export const uploadPDF = (formData, onProgress) =>
  api.post('/api/pdf/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total))
    },
  })

// ─── Subjects & Semesters ─────────────────────────────────────────────────────
export const searchSubjects = (q, semester = null) => {
  const params = {}
  if (q !== undefined && q !== null && q !== '') params.q = q
  if (semester) params.semester = semester
  return api.get('/api/subjects/search', { params })
}
export const getSemesters = () => api.get('/api/subjects/semesters')
export const getAllSubjects = (semester = null) =>
  api.get('/api/subjects/all', { params: semester ? { semester } : {} })
export const getSubject = (id) => api.get(`/api/subjects/${id}`)

// ─── Classes ──────────────────────────────────────────────────────────────────
export const getClasses = () => api.get('/api/classes')
export const getClass = (id) => api.get(`/api/classes/${id}`)
export const createClass = (data) => api.post('/api/classes', data)
export const deleteClass = (id) => api.delete(`/api/classes/${id}`)
export const getClassProgress = (classId) => api.get(`/api/classes/${classId}/progress`)
export const toggleTopicProgress = (classId, topicId, isCompleted) =>
  api.patch(`/api/classes/${classId}/topics/${topicId}/progress`, { is_completed: isCompleted })

// ─── AI ───────────────────────────────────────────────────────────────────────
export const sendChatMessage = (payload) => api.post('/api/ai/chat', payload)

export default api
