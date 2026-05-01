import { useState, useEffect } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'
import { Upload, FileText, Trash2, BookOpen, Loader2 } from 'lucide-react'

interface SidebarProps {
  currentDoc: string | null
  onSelectDoc: (doc: string) => void
}

interface Document {
  id: string
  name: string
  size: string
  date: string
  status?: string
}

import { API_BASE_URL } from '../config'

const API_BASE = API_BASE_URL

export default function Sidebar({ currentDoc, onSelectDoc }: SidebarProps) {
  const [docs, setDocs] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    fetchDocs()
  }, [])

  const fetchDocs = async () => {
    setLoading(true)
    try {
      const response = await axios.get(`${API_BASE}/docs`, { timeout: 5000 })
      setDocs(response.data)
    } catch (error) {
      toast.error('网络错误：无法连接到后端服务器')
    } finally {
      setLoading(false)
    }
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

        const newDoc: Document = {
          id: response.data.doc_id || Date.now().toString(),
          name: file.name,
          size: `${(file.size / 1024).toFixed(0)}KB`,
          date: new Date().toISOString().split('T')[0],
        }
        return newDoc
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
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-2 mb-4">
          <BookOpen className="w-6 h-6 text-indigo-600" />
          <span className="font-semibold text-gray-900">Nova-RAG</span>
        </div>

        <label className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg cursor-pointer transition-colors">
          {uploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm font-medium">上传中...</span>
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" />
              <span className="text-sm font-medium">上传文档</span>
            </>
          )}
          <input
            type="file"
            accept=".pdf,.docx,.xlsx,.csv,.md,.pptx,.txt"
            multiple
            className="hidden"
            onChange={handleUpload}
            disabled={uploading}
          />
        </label>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          文档列表
        </h3>
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
                  currentDoc === doc.id
                    ? 'bg-indigo-50 border border-indigo-200'
                    : 'hover:bg-gray-100'
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
      </div>
    </aside>
  )
}