import { useEffect, useRef, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  Sparkles, Send, Loader2, User, Bot, ArrowLeft,
  BookOpen, Zap, MessageSquare, RefreshCw
} from 'lucide-react'
import { getClasses, getClassProgress, sendChatMessage } from '../api'
import toast from 'react-hot-toast'
import ReactMarkdown from 'react-markdown'

const QUICK_PROMPTS = [
  { icon: '🗓️', label: 'Lesson Plan', text: 'Create a detailed 60-minute lesson plan for this topic.' },
  { icon: '💡', label: 'Explain Simply', text: 'Explain this topic in a simple way suitable for second-year engineering students.' },
  { icon: '📝', label: 'Examples', text: 'Give me 3 practical real-world examples I can explain on the board.' },
  { icon: '❓', label: 'Quiz Questions', text: 'Create a 10-question quiz with answers for this topic.' },
  { icon: '🖊️', label: 'Board Notes', text: 'What key points and diagrams should I write on the board?' },
  { icon: '🔗', label: 'Prerequisites', text: 'What prerequisite concepts should students know before I teach this topic?' },
]

function ChatBubble({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''} animate-slide-up`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
        isUser ? 'bg-primary-600' : 'bg-surface-600 border border-white/10'
      }`}>
        {isUser ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-primary-400" />}
      </div>
      <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
        isUser
          ? 'bg-primary-600 text-white rounded-tr-sm'
          : 'bg-surface-700 border border-white/5 text-slate-200 rounded-tl-sm'
      }`}>
        {isUser ? (
          <p>{msg.content}</p>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}

export default function AIAssistant() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const classId = searchParams.get('classId')
  const topicId = searchParams.get('topicId')
  const topicName = searchParams.get('topicName') || 'Selected Topic'

  const [classes, setClasses] = useState([])
  const [topics, setTopics] = useState([])
  const [selClassId, setSelClassId] = useState(classId || '')
  const [selTopicId, setSelTopicId] = useState(topicId || '')
  const [selTopicName, setSelTopicName] = useState(topicName)

  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    getClasses().then(r => setClasses(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    if (selClassId) {
      getClassProgress(selClassId)
        .then(r => setTopics(r.data.filter(t => !t.is_completed)))
        .catch(() => {})
    }
  }, [selClassId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const selectedClass = classes.find(c => String(c.id) === String(selClassId))
  const selectedTopic = topics.find(t => String(t.topic_id) === String(selTopicId))

  const handleSend = async () => {
    if (!input.trim()) return
    if (!selClassId || !selTopicId) {
      toast.error('Select a class and topic first')
      return
    }

    const userMsg = { role: 'user', content: input.trim() }
    const updatedMessages = [...messages, userMsg]
    setMessages(updatedMessages)
    setInput('')
    setSending(true)

    try {
      const res = await sendChatMessage({
        teacher_class_id: parseInt(selClassId),
        topic_id: parseInt(selTopicId),
        messages: updatedMessages,
      })
      setMessages(prev => [...prev, { role: 'model', content: res.data.reply }])
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'AI service error. Check your API key.'
      toast.error(errMsg)
      setMessages(prev => [...prev, { role: 'model', content: `⚠️ ${errMsg}` }])
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleQuickPrompt = (text) => {
    setInput(text)
    textareaRef.current?.focus()
  }

  return (
    <div className="min-h-screen pt-16 flex flex-col">
      {/* Top bar */}
      <div className="border-b border-white/5 bg-surface-900/80 backdrop-blur-xl px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-4">
          <button onClick={() => navigate(selClassId ? `/classes/${selClassId}` : '/classes')} className="btn-ghost p-2">
            <ArrowLeft className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary-400" />
            <span className="font-bold text-white">AI Teaching Assistant</span>
          </div>

          <div className="flex items-center gap-3">
            {/* Class selector */}
            <select
              value={selClassId}
              onChange={e => { setSelClassId(e.target.value); setSelTopicId(''); setMessages([]) }}
              className="input-field py-2 text-xs w-48"
            >
              <option value="">Select class…</option>
              {classes.map(c => (
                <option key={c.id} value={c.id}>{c.subject_code} – {c.section || ''}</option>
              ))}
            </select>
            {/* Topic selector */}
            <select
              value={selTopicId}
              onChange={e => {
                setSelTopicId(e.target.value)
                const t = topics.find(t => String(t.topic_id) === e.target.value)
                if (t) setSelTopicName(t.topic_name)
                setMessages([])
              }}
              className="input-field py-2 text-xs w-48"
              disabled={!selClassId}
            >
              <option value="">Select topic…</option>
              {topics.map(t => (
                <option key={t.topic_id} value={t.topic_id}>
                  U{t.unit_number}: {t.topic_name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="flex-1 flex max-w-6xl mx-auto w-full gap-0">
        {/* Context sidebar */}
        <div className="w-72 flex-shrink-0 border-r border-white/5 p-5 hidden lg:block">
          <div className="space-y-4">
            {/* Current context */}
            <div className="glass-card p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">RAG Context</p>
              {selectedClass ? (
                <div className="space-y-2">
                  <div>
                    <p className="text-xs text-slate-500">Subject</p>
                    <p className="text-sm font-semibold text-white">{selectedClass.subject_name}</p>
                  </div>
                  {selTopicId && (
                    <div>
                      <p className="text-xs text-slate-500">Topic</p>
                      <p className="text-sm font-semibold text-primary-300">{selTopicName}</p>
                    </div>
                  )}
                  {selectedClass.batch && (
                    <div>
                      <p className="text-xs text-slate-500">Class</p>
                      <p className="text-sm text-slate-300">{selectedClass.batch} · Sec {selectedClass.section}</p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-slate-500">Select a class and topic to enable RAG context.</p>
              )}
            </div>

            {/* Quick prompts */}
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Quick Prompts</p>
              <div className="space-y-1.5">
                {QUICK_PROMPTS.map((qp) => (
                  <button
                    key={qp.label}
                    onClick={() => handleQuickPrompt(qp.text)}
                    className="w-full text-left flex items-center gap-2 px-3 py-2.5 rounded-xl hover:bg-white/5 text-xs text-slate-400 hover:text-slate-200 transition-all border border-transparent hover:border-white/5"
                  >
                    <span className="text-base">{qp.icon}</span>
                    <span>{qp.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* New chat */}
            {messages.length > 0 && (
              <button
                onClick={() => setMessages([])}
                className="btn-ghost w-full justify-center text-xs"
              >
                <RefreshCw className="w-3.5 h-3.5" /> New Conversation
              </button>
            )}
          </div>
        </div>

        {/* Chat area */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-16">
                <div className="w-16 h-16 rounded-2xl bg-primary-600/20 border border-primary-500/30 flex items-center justify-center mb-4">
                  <Sparkles className="w-8 h-8 text-primary-400" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">AI Teaching Assistant</h2>
                <p className="text-slate-500 text-sm max-w-sm">
                  {selClassId && selTopicId
                    ? `Ready to help you plan "${selTopicName}". Ask anything or use a quick prompt.`
                    : 'Select a class and topic from the top bar to get started.'}
                </p>
                {(!selClassId || !selTopicId) && (
                  <div className="mt-6 grid grid-cols-2 gap-3 max-w-sm w-full">
                    {QUICK_PROMPTS.slice(0, 4).map(qp => (
                      <button
                        key={qp.label}
                        onClick={() => selClassId && selTopicId ? handleQuickPrompt(qp.text) : toast('Select a class and topic first')}
                        className="glass-card p-3 text-xs text-slate-400 hover:text-white hover:border-primary-500/30 transition-all text-left"
                      >
                        <span className="text-lg block mb-1">{qp.icon}</span>
                        {qp.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              messages.map((msg, i) => <ChatBubble key={i} msg={msg} />)
            )}
            {sending && (
              <div className="flex gap-3 animate-pulse">
                <div className="w-8 h-8 rounded-full bg-surface-600 border border-white/10 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-primary-400" />
                </div>
                <div className="bg-surface-700 border border-white/5 rounded-2xl rounded-tl-sm px-4 py-3">
                  <div className="flex gap-1.5 items-center h-5">
                    {[0, 1, 2].map(i => (
                      <div key={i} className="w-1.5 h-1.5 rounded-full bg-primary-500 animate-bounce"
                        style={{ animationDelay: `${i * 0.15}s` }} />
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <div className="border-t border-white/5 px-6 py-4">
            {/* Mobile quick prompts */}
            <div className="flex gap-2 mb-3 overflow-x-auto pb-1 lg:hidden">
              {QUICK_PROMPTS.map(qp => (
                <button
                  key={qp.label}
                  onClick={() => handleQuickPrompt(qp.text)}
                  className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-700 border border-white/5 text-xs text-slate-400 hover:text-white"
                >
                  <span>{qp.icon}</span>{qp.label}
                </button>
              ))}
            </div>
            <div className="flex gap-3 items-end">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={selClassId && selTopicId ? 'Ask anything about this topic…' : 'Select a class and topic to start…'}
                disabled={!selClassId || !selTopicId || sending}
                rows={1}
                className="input-field flex-1 resize-none max-h-32 py-3"
                style={{ minHeight: '48px' }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || sending || !selClassId || !selTopicId}
                className="btn-primary p-3 flex-shrink-0"
              >
                {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-xs text-slate-600 mt-2 text-center">
              Shift+Enter for new line · Responses grounded in your syllabus via RAG
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
