import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { X, Loader2, FileText } from 'lucide-react'
import { API_BASE_URL } from '../config'

const API_BASE = API_BASE_URL

interface PreviewData {
  doc_id: string
  name: string
  status: string
  content: string
}

interface Props {
  docId: string
  onClose: () => void
}

export default function DocumentPreviewer({ docId, onClose }: Props) {
  const [data, setData] = useState<PreviewData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    setData(null)

    fetch(`${API_BASE}/docs/${docId}/content`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [docId])

  return (
    <div className="w-1/2 min-w-0 border-l border-gray-200 bg-white flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="w-4 h-4 text-indigo-500 shrink-0" />
          <h3 className="text-sm font-semibold text-gray-800 truncate">
            {data?.name || '文档预览'}
          </h3>
          {data?.status && (
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
              data.status === 'ready' ? 'bg-green-100 text-green-700'
              : data.status === 'processing' ? 'bg-yellow-100 text-yellow-700'
              : 'bg-red-100 text-red-700'
            }`}>
              {data.status === 'ready' ? '已就绪' : data.status === 'processing' ? '处理中' : '失败'}
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors"
          title="关闭预览"
        >
          <X className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-400">
            <Loader2 className="w-8 h-8 animate-spin mb-3" />
            <span className="text-sm">正在加载文档内容...</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-20 text-red-400">
            <span className="text-sm">加载失败：{error}</span>
          </div>
        ) : data?.content ? (
          <div className="prose prose-sm max-w-none text-gray-700 leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.content}</ReactMarkdown>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-20 text-gray-400">
            <span className="text-sm">文档内容为空</span>
          </div>
        )}
      </div>
    </div>
  )
}
