import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import toast from 'react-hot-toast'
import { Send, Bot, User, ChevronRight, Loader2, ChevronDown, ChevronUp } from 'lucide-react'

interface ChatAreaProps {
  currentDoc: string | null
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  references?: { index: number; doc_id: string; content: string }[]
}

function parseThinkingContent(content: string): { thinking: string; answer: string } {
  const thinkingParts: string[] = []
  const answerParts: string[] = []
  let depth = 0
  let pos = 0
  const len = content.length

  while (pos < len) {
    const thinkStart = content.indexOf('<think>', pos)
    if (thinkStart === -1) {
      if (depth > 0) {
        thinkingParts.push(content.slice(pos))
      } else {
        answerParts.push(content.slice(pos))
      }
      break
    }

    if (depth === 0) {
      if (thinkStart > pos) {
        answerParts.push(content.slice(pos, thinkStart))
      }
    } else {
      thinkingParts.push(content.slice(pos, thinkStart))
    }

    pos = thinkStart + 8
    depth++
  }

  return {
    thinking: thinkingParts.join(''),
    answer: answerParts.join(''),
  }
}

function MessageBubble({ msg }: { msg: Message }) {
  const [thinkingOpen, setThinkingOpen] = useState(false)

  if (msg.role === 'user') {
    return (
      <div className="inline-block p-4 rounded-2xl bg-indigo-600 text-white">
        <div className="prose prose-sm max-w-none text-white">
          <ReactMarkdown>{msg.content}</ReactMarkdown>
        </div>
      </div>
    )
  }

  const { thinking, answer } = parseThinkingContent(msg.content)

  return (
    <div className="space-y-2">
      {thinking && (
        <details
          className="bg-gray-50 border border-gray-200 rounded-lg overflow-hidden"
          open={false}
        >
          <summary
            className="flex items-center gap-2 px-3 py-2 cursor-pointer select-none text-gray-500 hover:bg-gray-100 text-sm font-medium"
            onClick={() => setThinkingOpen(o => !o)}
          >
            {thinkingOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            <span>🤔</span>
            <span>AI 思考过程</span>
          </summary>
          <div className="px-4 py-2 text-sm text-gray-600 italic bg-gray-50">
            <ReactMarkdown>{thinking}</ReactMarkdown>
          </div>
        </details>
      )}
      {answer && (
        <div className="inline-block p-4 rounded-2xl bg-white shadow-sm border border-gray-200 text-gray-800">
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown>{answer}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  )
}

const API_BASE = 'http://127.0.0.1:8080/api/v1'

export default function ChatArea({ currentDoc }: ChatAreaProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const requestInFlight = useRef(false)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || streaming || requestInFlight.current) return

    requestInFlight.current = true

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setStreaming(true)

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
    }
    setMessages(prev => [...prev, assistantMessage])

    try {
      const response = await fetch(`${API_BASE}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [
            { role: 'user', content: input }
          ],
          stream: true
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`)
      }

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
          if (!line.trim()) continue
          if (line.startsWith('data:')) {
            const data = line.slice(5).trim()
            if (data === '[DONE]') continue

            try {
              const parsed = JSON.parse(data)
              if (parsed.content) {
                setMessages(prev => {
                  const updated = prev.map((m, i) =>
                    i === prev.length - 1 ? { ...m, content: m.content + parsed.content } : m
                  )
                  return updated
                })
              }
              if (parsed.done && parsed.references) {
                setMessages(prev => {
                  const updated = [...prev]
                  const lastMsg = updated[updated.length - 1]
                  lastMsg.references = parsed.references
                  return updated
                })
              }
            } catch {
              // Ignore parse errors for partial data
            }
          }
        }
      }
    } catch (error) {
      toast.error('网络错误：无法连接到 Go 后端服务器')
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
            <h2 className="text-xl font-semibold text-gray-700 mb-2">Lumina Insight 智能助手</h2>
            <p className="text-gray-500">请从左侧选择一个文档开始对话，或直接上传新文档</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map(msg => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                msg.role === 'user' ? 'bg-indigo-600' : 'bg-gray-200'
              }`}>
                {msg.role === 'user' ? (
                  <User className="w-4 h-4 text-white" />
                ) : (
                  <Bot className="w-4 h-4 text-gray-600" />
                )}
              </div>
              <div className={`max-w-2xl ${msg.role === 'user' ? 'text-right' : ''}`}>
                <div className="flex gap-3">
                  <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    msg.role === 'user' ? 'bg-indigo-600' : 'bg-gray-200'
                  }`}>
                    {msg.role === 'user' ? (
                      <User className="w-4 h-4 text-white" />
                    ) : (
                      <Bot className="w-4 h-4 text-gray-600" />
                    )}
                  </div>
                  <div>
                    <MessageBubble msg={msg} />
                    {msg.references && msg.references.length > 0 && (
                      <div className="mt-2 flex items-center gap-2 flex-wrap">
                        <span className="text-xs text-gray-500">参考来源：</span>
                        {msg.references.map((ref, idx) => (
                          <div key={idx} className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-xs text-gray-600">
                            <ChevronRight className="w-3 h-3" />
                            <span>[{ref.index}]</span>
                            <span className="font-medium">{ref.doc_id}</span>
                            <span className="text-gray-400">-</span>
                            <span>{ref.content}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
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
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                生成中...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                发送
              </>
            )}
          </button>
        </div>
      </form>
    </main>
  )
}