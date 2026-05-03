import { useState } from 'react'
import toast from 'react-hot-toast'
import {
  Upload, FileText, Trash2, Loader2, MessageSquare, Plus, Hash,
  CheckSquare, Square, X, FileType, Sparkles
} from 'lucide-react'
import { useDocuments } from '../hooks/useDocuments'
import { useConversations } from '../hooks/useConversations'
import { ThemeToggle } from './ThemeToggle'

interface SidebarProps {
  onConversationChange?: () => void
}

const statusConfig = {
  ready: { label: '就绪', color: 'bg-emerald-500', bg: 'bg-emerald-50 dark:bg-emerald-950/30' },
  processing: { label: '处理中', color: 'bg-amber-500 animate-pulse', bg: 'bg-amber-50 dark:bg-amber-950/30' },
  failed: { label: '失败', color: 'bg-red-500', bg: 'bg-red-50 dark:bg-red-950/30' },
} as const

function StatusBadge({ status }: { status?: string }) {
  const config = status ? statusConfig[status as keyof typeof statusConfig] : null
  if (!config) return null
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${config.bg} text-[var(--color-text-secondary)]`}>
      <span className={`w-1.5 h-1.5 rounded-full ${config.color}`} />
      {config.label}
    </span>
  )
}

function DocStats({ name }: { name: string }) {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const icons: Record<string, string> = {
    pdf: '📕', docx: '📘', xlsx: '📗', csv: '📙', md: '📄', txt: '📝', pptx: '📒'
  }
  const icon = icons[ext] || '📄'
  const colors: Record<string, string> = {
    pdf: 'text-red-500 bg-red-50 dark:bg-red-950/30',
    docx: 'text-blue-500 bg-blue-50 dark:bg-blue-950/30',
    xlsx: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-950/30',
    csv: 'text-green-500 bg-green-50 dark:bg-green-950/30',
    md: 'text-purple-500 bg-purple-50 dark:bg-purple-950/30',
    pptx: 'text-orange-500 bg-orange-50 dark:bg-orange-950/30',
  }
  const colorClass = colors[ext] || 'text-gray-500 bg-gray-50 dark:bg-gray-800/30'
  return (
    <span className={`inline-flex items-center justify-center w-6 h-6 rounded text-[11px] font-bold ${colorClass}`}>
      {icon}
    </span>
  )
}

export default function Sidebar({ onConversationChange }: SidebarProps) {
  const [tab, setTab] = useState<'docs' | 'chats'>('docs')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [batchDeleting, setBatchDeleting] = useState(false)
  const [uploading, setUploading] = useState(false)

  const {
    docs, loadingDocs, currentDoc, setCurrentDoc,
    handleUpload, handleDelete, handleBatchDelete, handlePreview,
  } = useDocuments()

  const {
    conversations, conversationId,
    handleSelectConversation, handleNewChat, handleDeleteConversation,
  } = useConversations()

  const toggleSelect = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === docs.length) setSelectedIds(new Set())
    else setSelectedIds(new Set(docs.map(d => d.id)))
  }

  const clearSelection = () => setSelectedIds(new Set())

  const onBatchDelete = async () => {
    if (selectedIds.size === 0) return
    if (!window.confirm(`确定要删除选中的 ${selectedIds.size} 个文档吗？`)) return
    setBatchDeleting(true)
    try {
      await handleBatchDelete(Array.from(selectedIds))
      setSelectedIds(new Set())
    } catch {
      toast.error('批量删除失败，请重试')
    } finally {
      setBatchDeleting(false)
    }
  }

  const onDeleteDoc = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!window.confirm('确定要删除该文档吗？')) return
    try {
      await handleDelete(id)
      setSelectedIds(prev => { const n = new Set(prev); n.delete(id); return n })
    } catch {
      toast.error('删除失败，请重试')
    }
  }

  const onSelectDoc = (id: string) => {
    setCurrentDoc(id)
    handlePreview(id)
  }

  const onDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    await handleDeleteConversation(id)
    onConversationChange?.()
  }

  const onSelectConversation = (id: string) => {
    handleSelectConversation(id)
    onConversationChange?.()
  }

  const onNewChat = () => {
    handleNewChat()
    onConversationChange?.()
  }

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    if (!fileList || fileList.length === 0) return
    const files = Array.from(fileList)
    setUploading(true)
    try {
      await handleUpload(files)
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const isAllSelected = docs.length > 0 && selectedIds.size === docs.length
  const readyCount = docs.filter(d => d.status === 'ready').length

  return (
    <aside className="w-80 flex flex-col h-full
                      bg-[var(--color-bg-secondary)] border-r border-[var(--color-border)]
                      transition-colors duration-200">
      {/* Header */}
      <div className="p-4 border-b border-[var(--color-border)]">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600
                          flex items-center justify-center shadow-md">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-[var(--color-text-primary)] text-sm">Nova-RAG</h1>
              <p className="text-[10px] text-[var(--color-text-muted)]">企业知识库问答</p>
            </div>
          </div>
          <ThemeToggle />
        </div>

        {/* Tab switcher */}
        <div className="flex gap-1 p-1 bg-[var(--color-bg-tertiary)] rounded-lg">
          <button onClick={() => setTab('docs')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium
                       rounded-md transition-all duration-150 ${
              tab === 'docs'
                ? 'bg-[var(--color-bg-elevated)] text-[var(--color-accent)] shadow-sm'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}>
            <FileType className="w-3.5 h-3.5" /> 文档库
          </button>
          <button onClick={() => setTab('chats')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium
                       rounded-md transition-all duration-150 ${
              tab === 'chats'
                ? 'bg-[var(--color-bg-elevated)] text-[var(--color-accent)] shadow-sm'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}>
            <MessageSquare className="w-3.5 h-3.5" /> 会话
          </button>
        </div>

        {tab === 'docs' && (
          <div className="mt-3 flex items-center justify-between">
            <label className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4
                             bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)]
                             text-white rounded-lg cursor-pointer transition-colors duration-150
                             shadow-sm">
              {uploading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /><span className="text-xs font-medium">上传中...</span></>
              ) : (
                <><Upload className="w-4 h-4" /><span className="text-xs font-medium">上传文档</span></>
              )}
              <input type="file" accept=".pdf,.docx,.xlsx,.csv,.md,.pptx,.txt" multiple
                     className="hidden" onChange={onUpload} disabled={uploading} />
            </label>
            {docs.length > 0 && (
              <span className="ml-2 text-[10px] text-[var(--color-text-muted)]">
                {readyCount}/{docs.length} 就绪
              </span>
            )}
          </div>
        )}

        {tab === 'chats' && (
          <button onClick={onNewChat}
            className="mt-3 flex items-center justify-center gap-2 w-full py-2.5 px-4
                     bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)]
                     text-white rounded-lg transition-colors duration-150 shadow-sm">
            <Plus className="w-4 h-4" /><span className="text-xs font-medium">新对话</span>
          </button>
        )}
      </div>

      {/* Batch action bar */}
      {tab === 'docs' && selectedIds.size > 0 && (
        <div className="px-4 py-2.5 bg-red-50 dark:bg-red-950/20 border-b border-red-100 dark:border-red-900/30
                       flex items-center justify-between animate-fade-in">
          <span className="text-xs text-red-600 dark:text-red-400 font-medium">
            已选 {selectedIds.size} 项
          </span>
          <div className="flex items-center gap-1.5">
            <button onClick={onBatchDelete} disabled={batchDeleting}
              className="flex items-center gap-1 px-2.5 py-1 text-xs bg-red-500 hover:bg-red-600
                       text-white rounded-md transition-colors disabled:opacity-50">
              {batchDeleting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
              删除
            </button>
            <button onClick={clearSelection}
              className="p-1 text-red-400 hover:text-red-600 transition-colors rounded-md hover:bg-red-50">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {tab === 'docs' ? (
          <div className="p-3">
            {docs.length > 0 && (
              <button onClick={toggleSelectAll}
                className="flex items-center gap-2 mb-2.5 px-2 py-1.5 text-[11px]
                         text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]
                         hover:bg-[var(--color-bg-tertiary)] rounded-md transition-colors">
                {isAllSelected
                  ? <CheckSquare className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                  : <Square className="w-3.5 h-3.5" />}
                <span className="font-medium">全选</span>
              </button>
            )}
            {loadingDocs ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-[var(--color-text-muted)]" />
              </div>
            ) : docs.length === 0 ? (
              <div className="text-center py-12">
                <FileText className="w-10 h-10 mx-auto mb-3 text-[var(--color-text-muted)] opacity-50" />
                <p className="text-sm text-[var(--color-text-muted)]">暂无文档</p>
                <p className="text-xs text-[var(--color-text-muted)] mt-1">上传文档开始智能问答</p>
              </div>
            ) : (
              <div className="space-y-1.5">
                {docs.map((doc, idx) => (
                  <div key={doc.id}
                    onClick={() => onSelectDoc(doc.id)}
                    className={`group flex items-center gap-2.5 p-2.5 rounded-lg cursor-pointer
                               transition-all duration-150 animate-slide-up ${
                      currentDoc === doc.id
                        ? 'bg-[var(--color-accent-soft)] border border-[var(--color-accent)]/30'
                        : 'hover:bg-[var(--color-bg-tertiary)] border border-transparent'
                    }`}
                    style={{ animationDelay: `${idx * 30}ms` }}>
                    <button onClick={(e) => toggleSelect(doc.id, e)}
                      className="shrink-0 text-[var(--color-text-muted)] hover:text-[var(--color-accent)]
                               transition-colors p-0.5 -ml-0.5 rounded">
                      {selectedIds.has(doc.id)
                        ? <CheckSquare className="w-4 h-4 text-[var(--color-accent)]" />
                        : <Square className="w-4 h-4" />}
                    </button>
                    <DocStats name={doc.name} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                          {doc.name}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {doc.size && (
                          <span className="text-[10px] text-[var(--color-text-muted)]">{doc.size}</span>
                        )}
                        <StatusBadge status={doc.status} />
                      </div>
                    </div>
                    <button onClick={(e) => onDeleteDoc(doc.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1.5
                               hover:bg-red-50 dark:hover:bg-red-950/30 hover:text-red-500
                               rounded-md transition-all duration-150" title="删除文档">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="p-3">
            <h3 className="flex items-center gap-1.5 text-[11px] font-semibold
                         text-[var(--color-text-muted)] uppercase tracking-wider px-2 mb-2.5">
              <Hash className="w-3 h-3" /> 历史会话
            </h3>
            {conversations.length === 0 ? (
              <div className="text-center py-12">
                <MessageSquare className="w-10 h-10 mx-auto mb-3 text-[var(--color-text-muted)] opacity-50" />
                <p className="text-sm text-[var(--color-text-muted)]">暂无会话记录</p>
              </div>
            ) : (
              <div className="space-y-1">
                {conversations.map((conv, idx) => (
                  <div key={conv.id} onClick={() => onSelectConversation(conv.id)}
                    className={`group flex items-center gap-2.5 p-2.5 rounded-lg cursor-pointer
                               transition-all duration-150 animate-slide-up ${
                      conversationId === conv.id
                        ? 'bg-[var(--color-accent-soft)] border border-[var(--color-accent)]/30'
                        : 'hover:bg-[var(--color-bg-tertiary)] border border-transparent'
                    }`}
                    style={{ animationDelay: `${idx * 30}ms` }}>
                    <Hash className="w-4 h-4 text-[var(--color-text-muted)] shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                        {conv.title}
                      </p>
                      <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">
                        {new Date(conv.updated_at).toLocaleDateString('zh-CN', {
                          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                        })}
                      </p>
                    </div>
                    <button onClick={(e) => onDeleteConversation(conv.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1.5
                               hover:bg-red-50 dark:hover:bg-red-950/30 hover:text-red-500
                               rounded-md transition-all duration-150" title="删除会话">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  )
}