import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './context/AuthContext'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import SubjectDetails from './pages/SubjectDetails'
import MyClasses from './pages/MyClasses'
import TeacherWorkspace from './pages/TeacherWorkspace'
import AIAssistant from './pages/AIAssistant'
import Auth from './pages/Auth'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Auth initialMode="login" />} />
          <Route path="/register" element={<Auth initialMode="register" />} />
          <Route path="/subjects/:id" element={<SubjectDetails />} />
          <Route path="/classes" element={<MyClasses />} />
          <Route path="/classes/:id" element={<TeacherWorkspace />} />
          <Route path="/classes/:id/plan" element={<AIAssistant />} />
          <Route path="/ai" element={<AIAssistant />} />
        </Routes>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#12142b',
              color: '#e2e8f0',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '12px',
              fontSize: '13px',
            },
            success: { iconTheme: { primary: '#10b981', secondary: '#fff' } },
            error: { iconTheme: { primary: '#ff5240', secondary: '#fff' } },
          }}
        />
      </AuthProvider>
    </BrowserRouter>
  )
}
