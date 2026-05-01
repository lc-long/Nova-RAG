import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import mammoth from 'mammoth'
import { X, Loader2, FileText, Download, ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from 'lucide-react'
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

function fetchAsArrayBuffer(url: string): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('GET', url, true)
    xhr.responseType = 'arraybuffer'
    xhr.onload = () => {
      if (xhr.status === 200) {
        resolve(xhr.response)
      } else {
        reject(new Error(`HTTP ${xhr.status}`))
      }
    }
    xhr.onerror = () => reject(new Error('Network error'))
    xhr.send()
  })
}

export default function DocumentPreviewer({ docId, onClose }: Props) {
  const [data, setData] = useState<PreviewData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [docxHtml, setDocxHtml] = useState<string | null>(null)

  const [pdfDoc, setPdfDoc] = useState<any>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [scale, setScale] = useState(2)
  const [rendering, setRendering] = useState(false)

  const canvasRef = useRef<HTMLCanvasElement>(null)
  const pdfDocRef = useRef<any>(null)
  const renderingTaskRef = useRef<any>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    setData(null)
    setDocxHtml(null)
    setPdfDoc(null)
    pdfDocRef.current = null
    setCurrentPage(1)
    setTotalPages(0)

    fetch(`${API_BASE}/docs/${docId}/content`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [docId])

  useEffect(() => {
    const ext = data?.name ? getFileExtension(data.name) : ''
    if (ext !== '.docx' || !docId) return

    let cancelled = false
    fetchAsArrayBuffer(`${API_BASE}/docs/${docId}/preview`)
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
    const ext = data?.name ? getFileExtension(data.name) : ''
    if (ext !== '.pdf' || !docId) return

    let cancelled = false

    const loadPdf = async () => {
      try {
        const arrayBuffer = await fetchAsArrayBuffer(`${API_BASE}/docs/${docId}/preview`)
        if (cancelled) return

        const pdfjsLib = await import('pdfjs-dist')
        pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
          'pdfjs-dist/build/pdf.worker.min.mjs',
          import.meta.url
        ).toString()

        const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer })
        const doc = await loadingTask.promise

        if (cancelled) return

        pdfDocRef.current = doc
        setPdfDoc(doc)
        setTotalPages(doc.numPages)
        setCurrentPage(1)
      } catch (err) {
        if (!cancelled) {
          console.error('PDF loading failed:', err)
          setPdfDoc(null)
          pdfDocRef.current = null
        }
      }
    }

    loadPdf()

    return () => {
      cancelled = true
    }
  }, [data?.name, docId])

  const renderPage = useCallback(async (pageNum: number) => {
    const doc = pdfDocRef.current
    if (!doc || !canvasRef.current) return

    if (renderingTaskRef.current) {
      renderingTaskRef.current.cancel()
      renderingTaskRef.current = null
    }

    setRendering(true)
    try {
      const page = await doc.getPage(pageNum)
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')
      if (!ctx) return

      const viewport = page.getViewport({ scale })
      canvas.width = viewport.width
      canvas.height = viewport.height

      const renderTask = page.render({
        canvasContext: ctx,
        viewport: viewport,
      } as any)

      renderingTaskRef.current = renderTask
      await renderTask.promise
      renderingTaskRef.current = null
    } catch (err: any) {
      if (err?.name !== 'RenderingCancelledException') {
        console.error('Page rendering failed:', err)
      }
    } finally {
      setRendering(false)
    }
  }, [scale])

  useEffect(() => {
    if (pdfDoc && currentPage > 0) {
      renderPage(currentPage)
    }
  }, [pdfDoc, currentPage, renderPage])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handlePrevPage = useCallback(() => {
    if (currentPage > 1) {
      setCurrentPage(prev => prev - 1)
    }
  }, [currentPage])

  const handleNextPage = useCallback(() => {
    if (currentPage < totalPages) {
      setCurrentPage(prev => prev + 1)
    }
  }, [currentPage, totalPages])

  const handleZoomIn = useCallback(() => {
    setScale(prev => Math.min(prev + 0.5, 4))
  }, [])

  const handleZoomOut = useCallback(() => {
    setScale(prev => Math.max(prev - 0.5, 0.5))
  }, [])

  const handleDownload = useCallback(async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    try {
      const response = await fetch(`${API_BASE}/docs/${docId}/download`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = data?.name || 'document'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Download failed:', err)
    }
  }, [docId, data])

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
            <button
              onClick={handleDownload}
              className="p-2 hover:bg-gray-200 rounded-full transition-colors"
              title="下载原文件"
            >
              <Download className="w-4 h-4 text-gray-500" />
            </button>
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
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-center gap-3 px-4 py-2 bg-gray-50 border-b border-gray-200">
              <button
                onClick={handlePrevPage}
                disabled={currentPage <= 1}
                className="p-1.5 rounded-lg hover:bg-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-gray-600 min-w-[80px] text-center">
                {currentPage} / {totalPages}
              </span>
              <button
                onClick={handleNextPage}
                disabled={currentPage >= totalPages}
                className="p-1.5 rounded-lg hover:bg-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
              <div className="w-px h-5 bg-gray-300 mx-1" />
              <button
                onClick={handleZoomOut}
                className="p-1.5 rounded-lg hover:bg-gray-200 transition-colors"
                title="缩小"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <span className="text-sm text-gray-600 min-w-[50px] text-center">
                {Math.round(scale * 100)}%
              </span>
              <button
                onClick={handleZoomIn}
                className="p-1.5 rounded-lg hover:bg-gray-200 transition-colors"
                title="放大"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-auto bg-gray-100 flex justify-center p-4 relative">
              {rendering && (
                <div className="absolute inset-0 flex items-center justify-center bg-white/50 z-10 pointer-events-none">
                  <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                </div>
              )}
              <canvas
                ref={canvasRef}
                className="shadow-lg bg-white"
              />
            </div>
          </div>
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
              <button
                onClick={handleDownload}
                className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white
                           text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
              >
                <Download className="w-4 h-4" />
                下载原文件
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
