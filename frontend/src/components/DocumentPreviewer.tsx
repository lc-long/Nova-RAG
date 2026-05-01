import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import mammoth from 'mammoth'
import { X, Loader2, FileText, Download } from 'lucide-react'
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

function getFileExtension(name: string): string {
  const dot = name.lastIndexOf('.')
  return dot >= 0 ? name.slice(dot).toLowerCase() : ''
}

export default function DocumentPreviewer({ docId, onClose }: Props) {
  const [data, setData] = useState<PreviewData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [docxHtml, setDocxHtml] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    setData(null)
    setDocxHtml(null)

    fetch(`${API_BASE}/docs/${docId}/content`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [docId])

  // DOCX: fetch file blob and convert to HTML via mammoth
  useEffect(() => {
    const ext = data?.name ? getFileExtension(data.name) : ''
    if (ext !== '.docx' || !docId) return

    let cancelled = false
    fetch(`${API_BASE}/docs/${docId}/download`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.arrayBuffer()
      })
      .then(arrayBuffer => mammoth.convertToHtml({ arrayBuffer }))
      .then(result => {
        if (!cancelled) setDocxHtml(result.value)
      })
      .catch(() => {
        if (!cancelled) setDocxHtml(null)
      })

    return () => { cancelled = true }
  }, [data?.name, docId])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const ext = data?.name ? getFileExtension(data.name) : ''
  const isPdf = ext === '.pdf'
  const isDocx = ext === '.docx'
  const isMd = ext === '.md'
  const isTxt = ext === '.txt'
  const isCsv = ext === '.csv'

  const statusLabel = data?.status === 'ready' ? '已就绪'
    : data?.status === 'processing' ? '处理中'
    : data?.status === 'failed' ? '失败' : null

  const statusColor = data?.status === 'ready' ? 'bg-green-50 text-green-600 ring-green-500/20'
    : data?.status === 'processing' ? 'bg-yellow-50 text-yellow-600 ring-yellow-500/20'
    : 'bg-red-50 text-red-600 ring-red-500/20'

  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200 shadow-2xl">
      {/* Sticky header */}
      <div className="sticky top-0 z-10 flex items-center justify-between px-5 py-3.5
                      border-b border-gray-200 bg-gray-50/80 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <div className="p-1.5 bg-indigo-50 rounded-lg shrink-0">
            <FileText className="w-4 h-4 text-indigo-500" />
          </div>
          <h3 className="text-sm font-semibold text-gray-800 truncate max-w-[280px]">
            {data?.name || '文档预览'}
          </h3>
          {statusLabel && (
            <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded-full font-medium ring-1 ${statusColor}`}>
              {statusLabel}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {data && (
            <a
              href={`${API_BASE}/docs/${docId}/download`}
              target="_blank"
              rel="noopener noreferrer"
              download
              className="p-2 hover:bg-gray-200 rounded-full transition-colors"
              title="下载原文件"
            >
              <Download className="w-4 h-4 text-gray-500" />
            </a>
          )}
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-200 rounded-full transition-colors"
            title="关闭预览 (Esc)"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-hidden">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <Loader2 className="w-8 h-8 animate-spin mb-3" />
            <span className="text-sm">正在加载文档内容...</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full text-red-400">
            <span className="text-sm">加载失败：{error}</span>
          </div>
        ) : isPdf ? (
          <iframe
            src={`${API_BASE}/docs/${docId}/preview?t=${Date.now()}`}
            className="w-full h-full border-0"
            title={data?.name}
          />
        ) : isDocx ? (
          docxHtml ? (
            <div className="h-full overflow-y-auto p-8">
              <div
                className="prose prose-sm md:prose-base max-w-none text-gray-700 leading-relaxed"
                dangerouslySetInnerHTML={{ __html: docxHtml }}
              />
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <Loader2 className="w-8 h-8 animate-spin mb-3" />
              <span className="text-sm">正在解析 Word 文档...</span>
            </div>
          )
        ) : isMd && data?.content ? (
          <div className="h-full overflow-y-auto p-6 md:p-8">
            <div className="prose prose-sm md:prose-base max-w-none text-gray-700
                            leading-relaxed whitespace-pre-wrap break-words">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.content}</ReactMarkdown>
            </div>
          </div>
        ) : (isTxt || isCsv) && data?.content ? (
          <div className="h-full overflow-y-auto p-6 md:p-8">
            <pre className="whitespace-pre-wrap break-words font-mono text-sm text-gray-700 leading-relaxed">
              {data.content}
            </pre>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 px-8">
            <div className="p-4 bg-gray-50 rounded-2xl border border-gray-200 text-center max-w-xs">
              <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm font-medium text-gray-600 mb-1">{data?.name}</p>
              <p className="text-xs text-gray-400 mb-4">
                该格式暂不支持在线预览
              </p>
              <a
                href={`${API_BASE}/docs/${docId}/download`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white
                           text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
              >
                <Download className="w-4 h-4" />
                下载原文件
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
