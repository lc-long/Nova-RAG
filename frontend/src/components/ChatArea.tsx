import { useState, useRef, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'
import axios from 'axios'
import {
  Send, Bot, User, Loader2, Globe, FileText, Trash2, Download,
  Search, Wand2, X
} from 'lucide-react'
import type { DocItem, Reference } from '../types'
import { useChat } from '../hooks/useChat'
import { useAppStore } from '../store/useAppStore'
import { MessageBubble } from './chat/MessageBubble'
import { SourceCard } from './chat/SourceCard'
import { SourceModal } from './chat/SourceModal'
import { MentionPopover, MentionTags } from './chat/MentionPopover'
import { RAGMetricsPanel } from './chat/RAGMetricsPanel'
import { API_BASE_URL } from '../config'

const STORAGE_KEY = 'nova_chat_history'

interface ChatAreaProps {
  docs: DocItem[]
  onPreview?: (docId: string) => void
}

export default function ChatArea({ docs, onPreview }: ChatAreaProps) {
  const { messages, sendMessage, clearMessages, exportMarkdown, cancelStream } = useChat()
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

  useEffect(() => {
    if (!conversationId) {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(messages)) } catch { /* ignore */ }
    }
  }, [messages, conversationId])

  useEffect(() => {
    scrollToBottom()
  }, [messages.length, scrollToBottom])

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

  const handleCitationRate = async (citation: Reference, helpful: boolean) => {
    if (!conversationId) {
      toast.error('请先创建会话')
      return
    }
    try {
      await axios.post(`${API_BASE_URL}/citations/feedback`, {
        helpful,
        conversation_id: conversationId,
        query: messages.find(m => m.references?.some(r => r.index === citation.index))?.content || '',
        citation_index: citation.index,
        doc_id: citation.doc_id,
        content: citation.content,
      })
      toast.success(helpful ? '感谢反馈' : '已记录')
    } catch {
      toast.error('反馈失败')
    }
  }

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
    <main className="flex-1 flex flex-col bg-[var(--color-bg-primary)]
                      border-l border-[var(--color-border)]">
      {messages.length === 0 ? (
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center max-w-md animate-fade-in">
            <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600
                          flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Bot className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-xl font-semibold text-[var(--color-text-primary)] mb-2">
              Nova-RAG 智能助手
            </h2>
            <p className="text-sm text-[var(--color-text-secondary)] mb-4">
              基于检索增强生成的企业级知识库问答系统
            </p>
            <div className="flex flex-col gap-2 text-left bg-[var(--color-bg-secondary)]
                          rounded-xl p-4 border border-[var(--color-border)]">
              <div className="flex items-start gap-2 text-xs text-[var(--color-text-secondary)]">
                <Search className="w-3.5 h-3.5 mt-0.5 text-[var(--color-accent)] shrink-0" />
                <span><strong className="text-[var(--color-text-primary)]">@文档名</strong> 精准检索 - 在指定文档中搜索答案</span>
              </div>
              <div className="flex items-start gap-2 text-xs text-[var(--color-text-secondary)]">
                <Globe className="w-3.5 h-3.5 mt-0.5 text-[var(--color-accent)] shrink-0" />
                <span><strong className="text-[var(--color-text-primary)]">全局检索</strong> 跨所有文档进行语义搜索</span>
              </div>
              <div className="flex items-start gap-2 text-xs text-[var(--color-text-secondary)]">
                <Wand2 className="w-3.5 h-3.5 mt-0.5 text-[var(--color-accent)] shrink-0" />
                <span><strong className="text-[var(--color-text-primary)]">混合检索</strong> 向量 + BM25 + RRF 融合</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between px-5 pt-4 pb-2">
            <div className="flex items-center gap-3">
              <span className="text-xs text-[var(--color-text-muted)]">
                {messages.length} 条消息
              </span>
              {streaming && (
                <span className="flex items-center gap-1.5 text-xs text-[var(--color-accent)]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent)] animate-pulse" />
                  生成中
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <div className="flex items-center p-1 bg-[var(--color-bg-tertiary)] rounded-lg">
                <button onClick={() => setSearchScope('global')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md transition-all duration-150 ${
                    searchScope === 'global'
                      ? 'bg-[var(--color-bg-elevated)] text-[var(--color-accent)] font-medium shadow-sm'
                      : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
                  }`} title="全局搜索：跨所有文档检索">
                  <Globe className="w-3.5 h-3.5" /> 全局
                </button>
                <button onClick={() => setSearchScope('doc')} disabled={!currentDoc}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md transition-all duration-150
                             disabled:opacity-40 disabled:cursor-not-allowed ${
                    searchScope === 'doc'
                      ? 'bg-[var(--color-bg-elevated)] text-[var(--color-accent)] font-medium shadow-sm'
                      : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
                  }`} title={currentDoc ? `当前文档检索：仅在「${currentDoc}」中搜索` : '请先选择一个文档'}>
                  <FileText className="w-3.5 h-3.5" /> 当前文档
                </button>
              </div>
              <button onClick={exportMarkdown}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs
                         text-[var(--color-text-muted)] hover:text-[var(--color-accent)]
                         hover:bg-[var(--color-accent-soft)] rounded-lg transition-colors"
                title="导出为 Markdown">
                <Download className="w-3.5 h-3.5" />
              </button>
              {streaming ? (
                <button onClick={cancelStream}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs
                           text-red-500 hover:bg-red-50 rounded-lg transition-colors">
                  <X className="w-3.5 h-3.5" /> 停止
                </button>
              ) : (
                <button onClick={handleClearSession}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs
                           text-[var(--color-text-muted)] hover:text-red-500
                           hover:bg-red-50 rounded-lg transition-colors"
                  title="清空当前会话">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
            {messages.map(msg => (
              <div key={msg.id} className={`flex gap-3 animate-slide-up ${
                msg.role === 'user' ? 'flex-row-reverse' : ''
              }`}>
                <div className={`shrink-0 w-9 h-9 rounded-xl flex items-center justify-center
                               shadow-sm transition-transform ${
                  msg.role === 'user'
                    ? 'bg-gradient-to-br from-indigo-500 to-purple-600'
                    : 'bg-[var(--color-bg-tertiary)] border border-[var(--color-border)]'
                }`}>
                  {msg.role === 'user'
                    ? <User className="w-4 h-4 text-white" />
                    : <Bot className="w-4 h-4 text-[var(--color-text-secondary)]" />}
                </div>
                <div className="max-w-2xl">
                  <MessageBubble
                    msg={msg}
                    onCite={(idx) => handleCitationClick(msg, idx)}
                  />
                  {msg.references && msg.references.length > 0 && (
                    <div className="mt-3">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider flex items-center gap-1">
                          <FileText className="w-3 h-3" /> 参考来源
                        </span>
                        <div className="flex-1 h-px bg-[var(--color-border)]" />
                        <span className="text-[10px] text-[var(--color-text-muted)]">
                          {msg.references.length} 个来源
                        </span>
                      </div>
                      <div className="flex gap-2.5 overflow-x-auto pb-1 -mx-1 px-1">
                        {msg.references.map(ref => (
                          <SourceCard
                            key={ref.index}
                            reference={ref}
                            onClick={() => {
                              setModalRef(ref)
                              onPreview?.(ref.doc_id)
                            }}
                            showRating={true}
                            onRate={(helpful) => handleCitationRate(ref, helpful)}
                          />
                        ))}
                      </div>
                      <div className="mt-2.5">
                        <RAGMetricsPanel msg={msg} />
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

      <form onSubmit={handleSubmit} className="p-4 border-t border-[var(--color-border)]
                                           bg-[var(--color-bg-secondary)]">
        <div className="max-w-3xl mx-auto">
          <MentionTags docIds={mentionDocIds} docs={docs} onRemove={removeMention} />
          <div className="relative flex gap-2.5">
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
              className="flex-1 px-4 py-3 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)]
                       rounded-xl focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]
                       focus:border-transparent disabled:opacity-50
                       text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]
                       transition-all duration-150"
            />
            <button
              type="submit"
              disabled={streaming || !input.trim()}
              className="px-5 py-3 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)]
                       disabled:opacity-50 disabled:cursor-not-allowed
                       text-white rounded-xl font-medium text-sm
                       flex items-center gap-2 transition-colors duration-150 shadow-sm
                       hover:shadow-md active:scale-[0.98]"
            >
              {streaming ? (
                <><Loader2 className="w-4 h-4 animate-spin" /><span>生成</span></>
              ) : (
                <><Send className="w-4 h-4" /><span>发送</span></>
              )}
            </button>
          </div>
          <div className="flex items-center justify-between mt-2 px-1">
            <div className="flex items-center gap-3 text-[10px] text-[var(--color-text-muted)]">
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-[var(--color-bg-tertiary)] rounded border border-[var(--color-border)]">@</kbd>
                指定文档
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-[var(--color-bg-tertiary)] rounded border border-[var(--color-border)]">Tab</kbd>
                补全
              </span>
            </div>
            <span className="text-[10px] text-[var(--color-text-muted)]">
              Nova-RAG v2.0
            </span>
          </div>
        </div>
      </form>

      {modalRef && (
        <SourceModal
          reference={modalRef}
          onClose={() => setModalRef(null)}
          onRate={(helpful) => handleCitationRate(modalRef, helpful)}
        />
      )}
    </main>
  )
}