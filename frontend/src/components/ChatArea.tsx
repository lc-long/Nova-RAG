import { useState, useRef, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'
import { Send, Bot, User, Loader2, Globe, FileText, Trash2, Download } from 'lucide-react'
import type { DocItem, Reference } from '../types'
import { useChat } from '../hooks/useChat'
import { useAppStore } from '../store/useAppStore'
import { MessageBubble } from './chat/MessageBubble'
import { SourceCard } from './chat/SourceCard'
import { SourceModal } from './chat/SourceModal'
import { MentionPopover, MentionTags } from './chat/MentionPopover'

const STORAGE_KEY = 'nova_chat_history'

interface ChatAreaProps {
  docs: DocItem[]
  onPreview?: (docId: string) => void
}

export default function ChatArea({ docs, onPreview }: ChatAreaProps) {
  const { messages, sendMessage, clearMessages, exportMarkdown } = useChat()
  const { currentDoc, conversationId, setMessages } = useAppStore()

  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [searchScope, setSearchScope] = useState<'global' | 'doc'>('global')
  const [modalRef, setModalRef] = useState<Reference | null>(null)
  const [mentionDocIds, setMentionDocIds] = useState<string[]>([])
  const [showMention, setShowMention] = useState(false)
  const [mentionFilter, setMentionFilter] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  // Load conversation messages when conversationId changes
  useEffect(() => {
    if (conversationId) {
      const { loadConversationMessages } = useAppStore.getState()
      loadConversationMessages(conversationId)
    } else {
      try {
        const saved = localStorage.getItem(STORAGE_KEY)
        if (saved) {
          const parsed = JSON.parse(saved)
          if (Array.isArray(parsed) && parsed.length > 0) setMessages(parsed)
          else setMessages([])
        } else {
          setMessages([])
        }
      } catch { setMessages([]) }
    }
  }, [conversationId, setMessages])

  // Persist to localStorage (only for unsaved new chats)
  useEffect(() => {
    if (!conversationId) {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(messages)) } catch { /* ignore */ }
    }
  }, [messages, conversationId])

  useEffect(() => { scrollToBottom() }, [messages.length, scrollToBottom])

  const handleClearSession = () => {
    if (!window.confirm('确定要清空当前会话吗？')) return
    clearMessages()
    setMentionDocIds([])
  }

  const handleCitationClick = (msg: typeof messages[0], index: number) => {
    if (!msg.references) return
    const ref = msg.references.find(r => r.index === index)
    if (ref) setModalRef(ref)
  }

  // @ mention detection
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setInput(val)

    const lastAt = val.lastIndexOf('@')
    if (lastAt !== -1 && lastAt === val.length - 1) {
      setShowMention(true)
      setMentionFilter('')
    } else if (lastAt !== -1 && lastAt >= val.length - 20) {
      const afterAt = val.slice(lastAt + 1)
      if (!afterAt.includes(' ')) {
        setShowMention(true)
        setMentionFilter(afterAt)
      } else {
        setShowMention(false)
      }
    } else {
      setShowMention(false)
    }
  }

  const handleMentionSelect = (doc: DocItem) => {
    if (!mentionDocIds.includes(doc.id)) {
      setMentionDocIds(prev => [...prev, doc.id])
    }
    const lastAt = input.lastIndexOf('@')
    setInput(input.slice(0, lastAt))
    setShowMention(false)
    inputRef.current?.focus()
  }

  const removeMention = (docId: string) => {
    setMentionDocIds(prev => prev.filter(id => id !== docId))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || streaming) return

    setStreaming(true)
    const currentInput = input
    setInput('')
    setShowMention(false)

    let effectiveDocIds: string[] | null = mentionDocIds.length > 0 ? mentionDocIds : null
    if (!effectiveDocIds && searchScope === 'doc' && currentDoc) {
      effectiveDocIds = [currentDoc]
    }

    try {
      await sendMessage(currentInput, effectiveDocIds)
    } catch {
      toast.error('发送失败')
    } finally {
      setStreaming(false)
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
            <p className="text-gray-400 text-sm mt-2">输入 @ 可指定文档进行精准检索</p>
          </div>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between px-6 pt-4">
            <span className="text-sm text-gray-400">{messages.length} 条消息</span>
            <div className="flex items-center gap-3">
              <div className="flex items-center bg-gray-100 rounded-lg p-1 gap-1">
                <button onClick={() => setSearchScope('global')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
                    searchScope === 'global' ? 'bg-white shadow-sm text-indigo-600 font-medium' : 'text-gray-500 hover:text-gray-700'
                  }`} title="全局搜索：跨所有文档检索">
                  <Globe className="w-4 h-4" /> 全局
                </button>
                <button onClick={() => setSearchScope('doc')} disabled={!currentDoc}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                    searchScope === 'doc' ? 'bg-white shadow-sm text-indigo-600 font-medium' : 'text-gray-500 hover:text-gray-700'
                  }`} title={currentDoc ? `当前文档检索：仅在「${currentDoc}」中搜索` : '请先选择一个文档'}>
                  <FileText className="w-4 h-4" /> 当前文档
                </button>
              </div>
              <button onClick={exportMarkdown}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                title="导出为 Markdown">
                <Download className="w-4 h-4" /> 导出
              </button>
              <button onClick={handleClearSession}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                title="清空当前会话">
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
                          <SourceCard key={ref.index} reference={ref} onClick={() => { setModalRef(ref); onPreview?.(ref.doc_id) }} />
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
        <div className="max-w-4xl mx-auto">
          <MentionTags docIds={mentionDocIds} docs={docs} onRemove={removeMention} />
          <div className="relative flex gap-3">
            {showMention && (
              <MentionPopover docs={docs} filter={mentionFilter} onSelect={handleMentionSelect} />
            )}
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={handleInputChange}
              onKeyDown={(e) => { if (e.key === 'Escape') setShowMention(false) }}
              placeholder="输入您的问题... (输入 @ 指定文档)"
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
        </div>
      </form>

      {modalRef && <SourceModal reference={modalRef} onClose={() => setModalRef(null)} />}
    </main>
  )
}
