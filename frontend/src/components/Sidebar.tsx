import { useState, useEffect } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'
import { Upload, FileText, Trash2, BookOpen, Loader2, MessageSquare, Plus, Hash } from 'lucide-react'

interface SidebarProps {
  currentDoc: string | null
  onSelectDoc: (doc: string) => void
  currentConversation: string | null
  onSelectConversation: (id: string | null) => void
  refreshTrigger: number
}

interface Document {
  id: string
  name: string
  size: string
  date: string
  status?: string
}

interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
}

import { API_BASE_URL } from '../config'

const API_BASE = API_BASE_URL

type TabType = 'docs' | 'chats'

export default function Sidebar({ currentDoc, onSelectDoc, currentConversation, onSelectConversation, refreshTrigger }: SidebarProps) {
  const [tab, setTab] = useState<TabType>('docs')
  const [docs, setDocs] = useState<Document[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)

  useEffect(() => { fetchDocs() }, [])
  useEffect(() => { fetchConversations() }, [refreshTrigger])

  const fetchDocs = async () => {
    setLoading(true)
    try {
      const response = await axios.get(`${API_BASE}/docs`, { timeout: 5000 })
      setDocs(response.data)
    } catch {
      toast.error('网络错误：无法连接到后端服务器')
    } finally {
      setLoading(false)
    }
  }

  const fetchConversations = async () => {
    try {
      const response = await axios.get(`${API_BASE}/conversations`, { timeout: 5000 })
      setConversations(response.data)
    } catch { /* silent */ }
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!window.confirm('确定要删除该文档吗？')) return
    try {
      await axios.delete(`${API_BASE}/docs/${id}`)
      setDocs(prev => prev.filter(d => d.id !== id))
      toast.success('文档已删除')
    } catch {
      toast.error('删除失败，请重试')
    }
  }

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await axios.delete(`${API_BASE}/conversations/${id}`)
      setConversations(prev => prev.filter(c => c.id !== id))
      if (currentConversation === id) onSelectConversation(null)
    } catch { /* silent */ }
  }

  const handleNewChat = () => {
    onSelectConversation(null)
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    if (!fileList || fileList.length === 0) return

    const files = Array.from(fileList)
    setUploading(true)

    const results = await Promise.allSettled(
      files.map(async (file) => {
        const formData = new FormData()
        formData.append('file', file)
        const response = await axios.post(`${API_BASE}/docs/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 60000,
        })
        return {
          id: response.data.id || Date.now().toString(),
          name: file.name,
          size: `${(file.size / 1024).toFixed(0)}KB`,
          date: new Date().toISOString().split('T')[0],
        } as Document
      })
    )

    const succeeded: Document[] = []
    const failed: string[] = []
    results.forEach((r, i) => {
      if (r.status === 'fulfilled') succeeded.push(r.value)
      else failed.push(files[i].name)
    })

    if (succeeded.length > 0) {
      setDocs(prev => [...succeeded, ...prev])
      toast.success(`成功上传 ${succeeded.length} 个文档`)
    }
    if (failed.length > 0) {
      toast.error(`以下文件上传失败：${failed.join(', ')}`)
    }

    setUploading(false)
    e.target.value = ''
    fetchDocs()
  }

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
          <button
            onClick={() => setTab('docs')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
              tab === 'docs' ? 'bg-white shadow-sm text-indigo-600 font-medium' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <FileText className="w-3.5 h-3.5" /> 文档库
          </button>
          <button
            onClick={() => setTab('chats')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
              tab === 'chats' ? 'bg-white shadow-sm text-indigo-600 font-medium' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" /> 会话
          </button>
        </div>

        {/* Upload button — only on docs tab */}
        {tab === 'docs' && (
          <label className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg cursor-pointer transition-colors">
            {uploading ? (
              <><Loader2 className="w-4 h-4 animate-spin" /><span className="text-sm font-medium">上传中...</span></>
            ) : (
              <><Upload className="w-4 h-4" /><span className="text-sm font-medium">上传文档</span></>
            )}
            <input type="file" accept=".pdf,.docx,.xlsx,.csv,.md,.pptx,.txt" multiple className="hidden" onChange={handleUpload} disabled={uploading} />
          </label>
        )}

        {/* New chat button — only on chats tab */}
        {tab === 'chats' && (
          <button
            onClick={handleNewChat}
            className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" /><span className="text-sm font-medium">新对话</span>
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {tab === 'docs' ? (
          <>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">文档列表</h3>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            ) : docs.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-8">暂无文档，请上传</p>
            ) : (
              <div className="space-y-2">
                {docs.map(doc => (
                  <div
                    key={doc.id}
                    onClick={() => onSelectDoc(doc.id)}
                    className={`group flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${
                      currentDoc === doc.id ? 'bg-indigo-50 border border-indigo-200' : 'hover:bg-gray-100'
                    }`}
                  >
                    <FileText className="w-5 h-5 text-gray-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{doc.name}</p>
                      <p className="text-xs text-gray-500">{doc.size}</p>
                    </div>
                    <button
                      onClick={(e) => handleDelete(doc.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 hover:text-red-500 rounded transition-opacity"
                      title="删除文档"
                    >
                      <Trash2 className="w-4 h-4" />
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
                  <div
                    key={conv.id}
                    onClick={() => onSelectConversation(conv.id)}
                    className={`group flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${
                      currentConversation === conv.id ? 'bg-indigo-50 border border-indigo-200' : 'hover:bg-gray-100'
                    }`}
                  >
                    <Hash className="w-5 h-5 text-gray-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{conv.title}</p>
                      <p className="text-xs text-gray-500">{new Date(conv.updated_at).toLocaleDateString()}</p>
                    </div>
                    <button
                      onClick={(e) => handleDeleteConversation(conv.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 hover:text-red-500 rounded transition-opacity"
                      title="删除会话"
                    >
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
