import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import toast from 'react-hot-toast'
import { Send, Bot, User, Loader2, ChevronDown, ChevronUp, Trash2, Globe, FileText, X, ExternalLink } from 'lucide-react'


interface Reference {
  index: number
  doc_id: string
  source_doc?: string
  page_number?: number
  content: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  reasoning: string
  references?: Reference[]
}

/* ── Inline citation badge ── */
function CitationBadge({ index, onClick }: { index: number; onClick: () => void }) {
  return (
    <sup
      onClick={(e) => { e.stopPropagation(); onClick() }}
      className="cursor-pointer text-xs bg-blue-50 text-blue-600 hover:bg-blue-100
                 rounded px-1 py-0.5 mx-0.5 font-medium transition-colors select-none"
    >
      {index}
    </sup>
  )
}

/* ── Source card ── */
function SourceCard({ ref_, onClick }: { ref_: Reference; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 p-2 border border-gray-200 rounded-lg
                 bg-gray-50 hover:bg-gray-100 text-sm w-48 shadow-sm
                 transition-all text-left shrink-0"
    >
      <span className="text-base shrink-0">📄</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1">
          <span className="text-[10px] font-bold text-white bg-blue-500 rounded px-1 shrink-0">
            {ref_.index}
          </span>
          <span className="truncate text-gray-700 font-medium text-xs">
            {ref_.doc_id.slice(0, 8)}...
          </span>
        </div>
        <p className="text-[11px] text-gray-400 truncate mt-0.5">
          {ref_.content.slice(0, 40)}...
        </p>
      </div>
      <ExternalLink className="w-3 h-3 text-gray-300 shrink-0" />
    </button>
  )
}

/* ── Detail modal ── */
function SourceModal({ ref_, onClose }: { ref_: Reference; onClose: () => void }) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[70vh]
                   flex flex-col overflow-hidden border border-gray-200"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-lg">📄</span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-gray-800 truncate">{ref_.doc_id}</p>
              {ref_.page_number ? (
                <p className="text-xs text-gray-400">Page {ref_.page_number}</p>
              ) : null}
            </div>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="text-xs font-bold text-blue-500 mb-2">Source [{ref_.index}]</div>
          <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap bg-gray-50
                          rounded-lg p-4 border border-gray-100">
            {ref_.content}
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Parse [N] citations in markdown text, return React nodes ── */
function renderWithCitations(text: string, onCite: (index: number) => void): React.ReactNode {
  const parts = text.split(/(\[\d+\])/g)
  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/)
    if (match) {
      return <CitationBadge key={i} index={parseInt(match[1])} onClick={() => onCite(parseInt(match[1]))} />
    }
    return <span key={i}>{part}</span>
  })
}

/* ── Message bubble ── */
function MessageBubble({ msg, onCite }: { msg: Message; onCite: (index: number) => void }) {
  const [thinkingOpen, setThinkingOpen] = useState(false)

  if (msg.role === 'user') {
    return (
      <div className="inline-block p-4 rounded-2xl bg-indigo-600 text-white max-w-xl">
        <div className="prose prose-sm max-w-none text-white whitespace-pre-wrap">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
        </div>
      </div>
    )
  }

  const isStreaming = msg.reasoning && !msg.content

  return (
    <div className="space-y-2 max-w-xl">
      {msg.reasoning && (
        <details className="bg-gray-50 border border-gray-200 rounded-lg" open={false}>
          <summary
            className="flex items-center gap-2 px-3 py-2 cursor-pointer select-none text-gray-500 hover:bg-gray-100 text-sm font-medium"
            onClick={() => setThinkingOpen(o => !o)}
          >
            {thinkingOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            <span>🤔</span>
            <span>AI 思考过程</span>
            {isStreaming && <span className="ml-2 text-xs animate-pulse">（生成中...）</span>}
          </summary>
          <div className="px-4 py-2 text-sm text-gray-600 whitespace-pre-wrap bg-gray-50 border-t border-gray-100">
            {msg.reasoning}
          </div>
        </details>
      )}
      {msg.content && (
        <div className="inline-block p-4 rounded-2xl bg-white shadow-sm border border-gray-200 text-gray-800 max-w-xl">
          <div className="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap leading-relaxed">
            {renderWithCitations(msg.content, onCite)}
          </div>
        </div>
      )}
    </div>
  )
}

import { API_BASE_URL } from '../config'

const API_BASE = API_BASE_URL
const STORAGE_KEY = 'lumina_chat_history'

export default function ChatArea({ currentDoc }: { currentDoc: string | null }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [searchScope, setSearchScope] = useState<'global' | 'doc'>('global')
  const [modalRef, setModalRef] = useState<Reference | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const requestInFlight = useRef(false)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved) as Message[]
        if (Array.isArray(parsed) && parsed.length > 0) setMessages(parsed)
      }
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(messages)) } catch { /* ignore */ }
  }, [messages])

  useEffect(() => { scrollToBottom() }, [messages])

  const handleClearSession = () => {
    if (!window.confirm('确定要清空当前会话吗？')) return
    setMessages([])
    localStorage.removeItem(STORAGE_KEY)
  }

  const handleCitationClick = (msg: Message, index: number) => {
    if (!msg.references) return
    const ref = msg.references.find(r => r.index === index)
    if (ref) setModalRef(ref)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || streaming || requestInFlight.current) return

    requestInFlight.current = true
    const userMessage: Message = { id: Date.now().toString(), role: 'user', content: input, reasoning: '' }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setStreaming(true)

    const assistantMessage: Message = { id: (Date.now() + 1).toString(), role: 'assistant', content: '', reasoning: '' }
    setMessages(prev => [...prev, assistantMessage])

    try {
      const response = await fetch(`${API_BASE}/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: input }],
          stream: true,
          doc_id: searchScope === 'doc' && currentDoc ? currentDoc : null,
        }),
      })

      if (!response.ok) throw new Error(`HTTP error ${response.status}`)

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) throw new Error('No reader available')

      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data:')) continue
          const data = line.slice(5).trim()
          if (data === '[DONE]') continue
          try {
            const parsed = JSON.parse(data)
            if (parsed.type === 'reasoning') {
              setMessages(prev => prev.map((m, i) =>
                i === prev.length - 1 ? { ...m, reasoning: m.reasoning + parsed.content } : m
              ))
            }
            if (parsed.type === 'answer') {
              setMessages(prev => prev.map((m, i) =>
                i === prev.length - 1 ? { ...m, content: m.content + parsed.content } : m
              ))
            }
            if (parsed.done && parsed.references) {
              setMessages(prev => prev.map((m, i) =>
                i === prev.length - 1 ? { ...m, references: parsed.references } : m
              ))
            }
          } catch { /* ignore partial data */ }
        }
      }
    } catch (error) {
      toast.error('网络错误：无法连接到后端服务器')
      setMessages(prev => prev.map((m, i) =>
        i === prev.length - 1 ? { ...m, content: `错误：无法连接到后端服务 (${error})` } : m
      ))
    } finally {
      setStreaming(false)
      requestInFlight.current = false
    }
  }

  return (
    <main className="flex-1 flex flex-col bg-gray-50">
      {messages.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Bot className="w-16 h-16 text-indigo-300 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-700 mb-2">Nova-RAG 智能助手</h2>
            <p className="text-gray-500">请从左侧选择一个文档开始对话，或直接上传新文档</p>
          </div>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between px-6 pt-4">
            <span className="text-sm text-gray-400">{messages.length} 条消息</span>
            <div className="flex items-center gap-3">
              <div className="flex items-center bg-gray-100 rounded-lg p-1 gap-1">
                <button
                  onClick={() => setSearchScope('global')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
                    searchScope === 'global' ? 'bg-white shadow-sm text-indigo-600 font-medium' : 'text-gray-500 hover:text-gray-700'
                  }`}
                  title="全局搜索：跨所有文档检索"
                >
                  <Globe className="w-4 h-4" /> 全局
                </button>
                <button
                  onClick={() => setSearchScope('doc')}
                  disabled={!currentDoc}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                    searchScope === 'doc' ? 'bg-white shadow-sm text-indigo-600 font-medium' : 'text-gray-500 hover:text-gray-700'
                  }`}
                  title={currentDoc ? `当前文档检索：仅在「${currentDoc}」中搜索` : '请先选择一个文档'}
                >
                  <FileText className="w-4 h-4" /> 当前文档
                </button>
              </div>
              <button
                onClick={handleClearSession}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                title="清空当前会话"
              >
                <Trash2 className="w-4 h-4" /> 清空会话
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.map(msg => (
              <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                  msg.role === 'user' ? 'bg-indigo-600' : 'bg-gray-200'
                }`}>
                  {msg.role === 'user' ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-gray-600" />}
                </div>
                <div className="max-w-2xl">
                  <MessageBubble msg={msg} onCite={(idx) => handleCitationClick(msg, idx)} />
                  {msg.references && msg.references.length > 0 && (
                    <div className="mt-3">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Sources</span>
                        <div className="flex-1 h-px bg-gray-200" />
                      </div>
                      <div className="flex gap-2 overflow-x-auto pb-1">
                        {msg.references.map(ref => (
                          <SourceCard key={ref.index} ref_={ref} onClick={() => setModalRef(ref)} />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </>
      )}

      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 bg-white">
        <div className="flex gap-3 max-w-4xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="输入您的问题..."
            disabled={streaming}
            className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
          >
            {streaming ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> 生成中...</>
            ) : (
              <><Send className="w-4 h-4" /> 发送</>
            )}
          </button>
        </div>
      </form>

      {modalRef && <SourceModal ref_={modalRef} onClose={() => setModalRef(null)} />}
    </main>
  )
}
