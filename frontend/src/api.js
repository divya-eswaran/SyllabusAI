import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 120000,
})

// ─── PDF ──────────────────────────────────────────────────────────────────────
export const uploadPDF = (formData, onProgress) =>
  api.post('/api/pdf/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total))
    },
  })

// ─── Subjects ─────────────────────────────────────────────────────────────────
export const searchSubjects = (q) => api.get('/api/subjects/search', { params: { q } })
export const getAllSubjects = () => api.get('/api/subjects/all')
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
