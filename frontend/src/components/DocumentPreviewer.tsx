import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import DOMPurify from 'dompurify'
import mammoth from 'mammoth'
import { X, Loader2, FileText, Download, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Highlighter } from 'lucide-react'
import { API_BASE_URL } from '../config'
import type { ChunkPosition } from '../types'

const API_BASE = API_BASE_URL

interface PreviewData {
  doc_id: string
  name: string
  status: string
  content: string
  chunks?: ChunkPosition[]
}

interface HighlightRange {
  start: number
  end: number
  citationIndex: number
}

interface Props {
  docId: string
  onClose: () => void
  highlightRanges?: HighlightRange[]
  onHighlightClick?: (citationIndex: number) => void
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
      if (xhr.status === 200) resolve(xhr.response)
      else reject(new Error(`HTTP ${xhr.status}`))
    }
    xhr.onerror = () => reject(new Error('Network error'))
    xhr.send()
  })
}

type RenderTask = { cancel: () => void }
type PdfDoc = any

export default function DocumentPreviewer({
  docId,
  onClose,
  highlightRanges = [],
  onHighlightClick
}: Props) {
  const [data, setData] = useState<PreviewData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [docxHtml, setDocxHtml] = useState<string | null>(null)
  const [pdfDoc, setPdfDoc] = useState<PdfDoc>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const RENDER_SCALE = 2
  const [zoom, setZoom] = useState(100)
  const [rendering, setRendering] = useState(false)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const pdfDocRef = useRef<PdfDoc>(null)
  const renderingTaskRef = useRef<RenderTask | null>(null)
  const prevDocIdRef = useRef<string | null>(null)
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (highlightRanges.length > 0 && contentRef.current) {
      const firstHighlight = highlightRanges[0]
      const textNode = contentRef.current.querySelector(`[data-pos="${firstHighlight.start}"]`)
      if (textNode) {
        textNode.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  }, [highlightRanges])

  const renderHighlightedContent = useCallback((content: string) => {
    if (highlightRanges.length === 0) {
      return <span>{content}</span>
    }

    const sortedRanges = [...highlightRanges].sort((a, b) => a.start - b.start)
    const result: React.ReactNode[] = []
    let lastEnd = 0

    sortedRanges.forEach((range, idx) => {
      if (range.start > lastEnd) {
        result.push(<span key={`text-${idx}`}>{content.slice(lastEnd, range.start)}</span>)
      }
      result.push(
        <mark
          key={`highlight-${idx}`}
          data-pos={range.start}
          className="bg-yellow-200 dark:bg-yellow-800/50 rounded px-0.5 cursor-pointer hover:bg-yellow-300 dark:hover:bg-yellow-700/50 transition-colors"
          onClick={() => onHighlightClick?.(range.citationIndex)}
          title={`引用 [${range.citationIndex}] - 点击查看详情`}
        >
          {content.slice(range.start, range.end)}
        </mark>
      )
      lastEnd = range.end
    })

    if (lastEnd < content.length) {
      result.push(<span key="text-end">{content.slice(lastEnd)}</span>)
    }

    return <>{result}</>
  }, [highlightRanges, onHighlightClick])

  useEffect(() => {
    if (prevDocIdRef.current === docId) return
    prevDocIdRef.current = docId
    setError(null)
    setData(null)
    setDocxHtml(null)
    setPdfDoc(null)
    pdfDocRef.current = null
    setCurrentPage(1)
    setTotalPages(0)
    fetch(`${API_BASE}/docs/${docId}/content`)
      .then(res => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json() })
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
      .then(result => { if (!cancelled) setDocxHtml(DOMPurify.sanitize(result.value)) })
      .catch(() => { if (!cancelled) setDocxHtml(null) })
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
          'pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url
        ).toString()
        const doc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
        if (cancelled) return
        pdfDocRef.current = doc
        setPdfDoc(doc)
        setTotalPages(doc.numPages)
        setCurrentPage(1)
      } catch {
        if (!cancelled) { setPdfDoc(null); pdfDocRef.current = null }
      }
    }
    loadPdf()
    return () => { cancelled = true }
  }, [data?.name, docId])

  const renderPage = useCallback(async (pageNum: number) => {
    const doc = pdfDocRef.current
    if (!doc || !canvasRef.current) return
    if (renderingTaskRef.current) { renderingTaskRef.current.cancel(); renderingTaskRef.current = null }
    setRendering(true)
    try {
      const page = await doc.getPage(pageNum)
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      const viewport = page.getViewport({ scale: RENDER_SCALE * (zoom / 100) })
      canvas.width = viewport.width
      canvas.height = viewport.height
      const renderTask = page.render({ canvasContext: ctx, viewport })
      renderingTaskRef.current = renderTask as unknown as RenderTask
      await renderTask.promise
      renderingTaskRef.current = null
    } catch (err) {
      if ((err as Error)?.name !== 'RenderingCancelledException') console.error('Page rendering failed:', err)
    } finally {
      setRendering(false)
    }
  }, [zoom])

  useEffect(() => {
    if (pdfDoc && currentPage > 0) renderPage(currentPage)
  }, [pdfDoc, currentPage, renderPage])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const ext = data?.name ? getFileExtension(data.name) : ''
  const isPdf = ext === '.pdf', isDocx = ext === '.docx', isMd = ext === '.md'
  const isTxt = ext === '.txt', isCsv = ext === '.csv'

  const statusConfig = {
    ready: { label: '已就绪', class: 'bg-emerald-50 text-emerald-600 border-emerald-200' },
    processing: { label: '处理中', class: 'bg-amber-50 text-amber-600 border-amber-200' },
    failed: { label: '失败', class: 'bg-red-50 text-red-500 border-red-200' },
  } as const

  return (
    <div className="h-full flex flex-col
                    bg-[var(--color-bg-secondary)] border-l border-[var(--color-border)]">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]
                      bg-[var(--color-bg-tertiary)] shrink-0">
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <div className="w-8 h-8 rounded-lg bg-[var(--color-accent-soft)] border border-[var(--color-accent)]/20
                        flex items-center justify-center shrink-0">
            <FileText className="w-4 h-4 text-[var(--color-accent)]" />
          </div>
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] truncate max-w-[240px]">
            {data?.name || '文档预览'}
          </h3>
          {data?.status && statusConfig[data.status as keyof typeof statusConfig] && (
            <span className={`shrink-0 text-[10px] px-2 py-0.5 rounded-full font-medium border
                            ${statusConfig[data.status as keyof typeof statusConfig].class}`}>
              {statusConfig[data.status as keyof typeof statusConfig].label}
            </span>
          )}
          {highlightRanges.length > 0 && (
            <span className="shrink-0 flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full
                           font-medium bg-yellow-50 text-yellow-700 dark:bg-yellow-950/30 dark:text-yellow-400
                           border border-yellow-200 dark:border-yellow-800">
              <Highlighter className="w-3 h-3" />
              {highlightRanges.length} 处高亮
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {data && (
            <button onClick={async (e) => {
              e.preventDefault(); e.stopPropagation()
              try {
                const response = await fetch(`${API_BASE}/docs/${docId}/download`)
                if (!response.ok) throw new Error(`HTTP ${response.status}`)
                const blob = await response.blob()
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url; a.download = data?.name || 'document'
                document.body.appendChild(a); a.click()
                document.body.removeChild(a); URL.revokeObjectURL(url)
              } catch { /* ignore */ }
            }}
              className="p-2 hover:bg-[var(--color-bg-secondary)] rounded-lg
                       text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]
                       transition-colors" title="下载原文件">
              <Download className="w-4 h-4" />
            </button>
          )}
          <button onClick={onClose}
            className="p-2 hover:bg-[var(--color-bg-secondary)] rounded-lg
                     text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]
                     transition-colors" title="关闭预览 (Esc)">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full text-[var(--color-text-muted)]">
            <Loader2 className="w-8 h-8 animate-spin mb-3" />
            <span className="text-sm">正在加载文档内容...</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full text-red-400">
            <span className="text-sm">加载失败：{error}</span>
          </div>
        ) : isPdf ? (
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-center gap-3 px-4 py-2.5
                          bg-[var(--color-bg-tertiary)] border-b border-[var(--color-border)]">
              <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage <= 1}
                className="p-1.5 rounded-lg hover:bg-[var(--color-bg-secondary)]
                         disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-[var(--color-text-secondary)] min-w-[80px] text-center font-medium">
                {currentPage} / {totalPages}
              </span>
              <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages}
                className="p-1.5 rounded-lg hover:bg-[var(--color-bg-secondary)]
                         disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
                <ChevronRight className="w-4 h-4" />
              </button>
              <div className="w-px h-5 bg-[var(--color-border)] mx-1" />
              <button onClick={() => setZoom(z => Math.max(z - 20, 50))}
                className="p-1.5 rounded-lg hover:bg-[var(--color-bg-secondary)] transition-colors">
                <ZoomOut className="w-4 h-4" />
              </button>
              <span className="text-sm text-[var(--color-text-secondary)] min-w-[50px] text-center">
                {zoom}%
              </span>
              <button onClick={() => setZoom(z => Math.min(z + 20, 300))}
                className="p-1.5 rounded-lg hover:bg-[var(--color-bg-secondary)] transition-colors">
                <ZoomIn className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-auto bg-[var(--color-bg-tertiary)] flex justify-center p-4 relative">
              {rendering && (
                <div className="absolute inset-0 flex items-center justify-center
                              bg-[var(--color-bg-secondary)]/50 z-10 pointer-events-none">
                  <Loader2 className="w-6 h-6 animate-spin text-[var(--color-text-muted)]" />
                </div>
              )}
              <canvas ref={canvasRef} className="shadow-lg bg-white rounded" />
            </div>
          </div>
        ) : isDocx ? (
          docxHtml ? (
            <div className="h-full overflow-y-auto p-6 md:p-8">
              <div className="prose prose-sm md:prose-base max-w-none text-[var(--color-text-secondary)]
                            leading-relaxed" dangerouslySetInnerHTML={{ __html: docxHtml }} />
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-[var(--color-text-muted)]">
              <Loader2 className="w-8 h-8 animate-spin mb-3" />
              <span className="text-sm">正在解析 Word 文档...</span>
            </div>
          )
        ) : isMd && data?.content ? (
          <div className="h-full overflow-y-auto p-6 md:p-8" ref={contentRef}>
            {highlightRanges.length > 0 ? (
              <div className="prose prose-sm md:prose-base max-w-none text-[var(--color-text-secondary)]
                            leading-relaxed whitespace-pre-wrap break-words">
                {renderHighlightedContent(data.content)}
              </div>
            ) : (
              <div className="prose prose-sm md:prose-base max-w-none text-[var(--color-text-secondary)]
                            leading-relaxed whitespace-pre-wrap break-words">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.content}</ReactMarkdown>
              </div>
            )}
          </div>
        ) : (isTxt || isCsv) && data?.content ? (
          <div className="h-full overflow-y-auto p-6 md:p-8" ref={contentRef}>
            <pre className="whitespace-pre-wrap break-words font-mono text-sm
                          text-[var(--color-text-secondary)] leading-relaxed">
              {renderHighlightedContent(data.content)}
            </pre>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full
                        text-[var(--color-text-muted)] px-8">
            <div className="p-6 bg-[var(--color-bg-tertiary)] rounded-2xl border border-[var(--color-border)]
                          text-center max-w-xs">
              <FileText className="w-12 h-12 mx-auto mb-4 text-[var(--color-text-muted)] opacity-50" />
              <p className="text-sm font-medium text-[var(--color-text-primary)] mb-1">{data?.name}</p>
              <p className="text-xs text-[var(--color-text-muted)] mb-4">该格式暂不支持在线预览</p>
              <button onClick={async (e) => {
                e.preventDefault()
                try {
                  const response = await fetch(`${API_BASE}/docs/${docId}/download`)
                  if (!response.ok) throw new Error(`HTTP ${response.status}`)
                  const blob = await response.blob()
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url; a.download = data?.name || 'document'
                  document.body.appendChild(a); a.click()
                  document.body.removeChild(a); URL.revokeObjectURL(url)
                } catch { /* ignore */ }
              }}
                className="inline-flex items-center gap-2 px-4 py-2
                         bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)]
                         text-white text-sm font-medium rounded-lg transition-colors">
                <Download className="w-4 h-4" /> 下载原文件
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}