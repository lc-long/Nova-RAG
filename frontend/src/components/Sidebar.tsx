import { useState } from 'react'
import toast from 'react-hot-toast'
import { Upload, FileText, Trash2, BookOpen, Loader2, MessageSquare, Plus, Hash, CheckSquare, Square, X } from 'lucide-react'
import { useDocuments } from '../hooks/useDocuments'
import { useConversations } from '../hooks/useConversations'

interface SidebarProps {
  onConversationChange?: () => void
}

/* Status dot indicator */
function StatusDot({ status }: { status?: string }) {
  const color = status === 'ready' ? 'bg-green-500'
    : status === 'processing' ? 'bg-yellow-400 animate-pulse'
    : status === 'failed' ? 'bg-red-500'
    : 'bg-gray-300'
  const title = status === 'ready' ? '解析成功'
    : status === 'processing' ? '入库中...'
    : status === 'failed' ? '解析失败'
    : '未知'
  return <span className={`w-2 h-2 rounded-full ${color} shrink-0`} title={title} />
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
    if (selectedIds.size === docs.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(docs.map(d => d.id)))
    }
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

  return (
    <aside className="w-72 bg-white border-r border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-2 mb-4">
          <BookOpen className="w-6 h-6 text-indigo-600" />
          <span className="font-semibold text-gray-900">Nova-RAG</span>
        </div>

        {/* Tab switcher */}
        <div className="flex bg-gray-100 rounded-lg p-1 gap-1 mb-3">
          <button onClick={() => setTab('docs')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
              tab === 'docs' ? 'bg-white shadow-sm text-indigo-600 font-medium' : 'text-gray-500 hover:text-gray-700'
            }`}>
            <FileText className="w-3.5 h-3.5" /> 文档库
          </button>
          <button onClick={() => setTab('chats')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
              tab === 'chats' ? 'bg-white shadow-sm text-indigo-600 font-medium' : 'text-gray-500 hover:text-gray-700'
            }`}>
            <MessageSquare className="w-3.5 h-3.5" /> 会话
          </button>
        </div>

        {tab === 'docs' && (
          <label className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg cursor-pointer transition-colors">
            {uploading ? (
              <><Loader2 className="w-4 h-4 animate-spin" /><span className="text-sm font-medium">上传中...</span></>
            ) : (
              <><Upload className="w-4 h-4" /><span className="text-sm font-medium">上传文档</span></>
            )}
            <input type="file" accept=".pdf,.docx,.xlsx,.csv,.md,.pptx,.txt" multiple className="hidden" onChange={onUpload} disabled={uploading} />
          </label>
        )}

        {tab === 'chats' && (
          <button onClick={onNewChat}
            className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors">
            <Plus className="w-4 h-4" /><span className="text-sm font-medium">新对话</span>
          </button>
        )}
      </div>

      {/* Batch action bar */}
      {tab === 'docs' && selectedIds.size > 0 && (
        <div className="px-4 py-2 bg-red-50 border-b border-red-100 flex items-center justify-between">
          <span className="text-xs text-red-600 font-medium">已选 {selectedIds.size} 项</span>
          <div className="flex items-center gap-2">
            <button onClick={onBatchDelete} disabled={batchDeleting}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50 transition-colors">
              {batchDeleting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
              删除
            </button>
            <button onClick={clearSelection} className="p-1 text-red-400 hover:text-red-600 transition-colors">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {tab === 'docs' ? (
          <>
            {/* Select all header */}
            {docs.length > 0 && (
              <button onClick={toggleSelectAll}
                className="flex items-center gap-2 mb-3 text-xs text-gray-400 hover:text-gray-600 transition-colors">
                {isAllSelected ? <CheckSquare className="w-3.5 h-3.5 text-indigo-500" /> : <Square className="w-3.5 h-3.5" />}
                <span className="font-medium uppercase tracking-wider">全选</span>
              </button>
            )}
            {loadingDocs ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            ) : docs.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-8">暂无文档，请上传</p>
            ) : (
              <div className="space-y-1">
                {docs.map(doc => (
                  <div key={doc.id} onClick={() => onSelectDoc(doc.id)}
                    className={`group flex items-center gap-2.5 p-2.5 rounded-lg cursor-pointer transition-all ${
                      currentDoc === doc.id ? 'bg-indigo-50 border border-indigo-200' : 'hover:bg-gray-100'
                    }`}>
                    {/* Checkbox */}
                    <button onClick={(e) => toggleSelect(doc.id, e)}
                      className="shrink-0 text-gray-300 hover:text-indigo-500 transition-colors">
                      {selectedIds.has(doc.id)
                        ? <CheckSquare className="w-4 h-4 text-indigo-500" />
                        : <Square className="w-4 h-4" />}
                    </button>
                    <StatusDot status={doc.status} />
                    <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{doc.name}</p>
                      <p className="text-[11px] text-gray-400">{doc.size}</p>
                    </div>
                    <button onClick={(e) => onDeleteDoc(doc.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 hover:text-red-500 rounded transition-opacity"
                      title="删除文档">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">历史会话</h3>
            {conversations.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-8">暂无会话记录</p>
            ) : (
              <div className="space-y-2">
                {conversations.map(conv => (
                  <div key={conv.id} onClick={() => onSelectConversation(conv.id)}
                    className={`group flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${
                      conversationId === conv.id ? 'bg-indigo-50 border border-indigo-200' : 'hover:bg-gray-100'
                    }`}>
                    <Hash className="w-5 h-5 text-gray-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{conv.title}</p>
                      <p className="text-xs text-gray-500">{new Date(conv.updated_at).toLocaleDateString()}</p>
                    </div>
                    <button onClick={(e) => onDeleteConversation(conv.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 hover:text-red-500 rounded transition-opacity"
                      title="删除会话">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </aside>
  )
}
