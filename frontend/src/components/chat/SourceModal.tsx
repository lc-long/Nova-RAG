import { useEffect } from 'react'
import { X, FileText, Hash, Layers, ArrowRight, ThumbsUp, ThumbsDown } from 'lucide-react'
import type { Reference } from '../../types'

interface SourceModalProps {
  reference: Reference
  onClose: () => void
  onRate?: (helpful: boolean) => void
}

export function SourceModal({ reference, onClose, onRate }: SourceModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const score = reference.score ?? 0
  const scorePercent = Math.round(score * 100)

  const getScoreColor = () => {
    if (score >= 0.8) return { bar: 'bg-emerald-500', text: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-950/20' }
    if (score >= 0.6) return { bar: 'bg-amber-500', text: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-950/20' }
    return { bar: 'bg-red-500', text: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-950/20' }
  }
  const scoreColors = getScoreColor()

  const getScoreTypeLabel = () => {
    if (reference.score_type === 'rerank') return 'Cross-Encoder 重排序'
    if (reference.score_type === 'vector') return '向量检索'
    if (reference.score_type === 'bm25') return '关键词检索'
    return '混合检索 (RRF)'
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in"
         onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div onClick={(e) => e.stopPropagation()}
        className="relative bg-[var(--color-bg-secondary)] rounded-2xl shadow-2xl
                   max-w-lg w-full max-h-[80vh] flex flex-col overflow-hidden
                   border border-[var(--color-border)] animate-slide-up">
        <div className="flex items-center justify-between p-4 border-b border-[var(--color-border)]
                       bg-[var(--color-bg-tertiary)]">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <div className="w-10 h-10 rounded-xl bg-[var(--color-accent-soft)] border border-[var(--color-accent)]/20
                          flex items-center justify-center shrink-0">
              <FileText className="w-5 h-5 text-[var(--color-accent)]" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold text-[var(--color-text-primary)] truncate max-w-[180px]">
                  {reference.doc_id}
                </p>
                <span className={`flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-bold border ${scoreColors.bg} ${scoreColors.text} border-current/20`}>
                  <Layers className="w-3 h-3" /> {scorePercent}%
                </span>
              </div>
              <div className="flex items-center gap-2 mt-0.5 text-[10px] text-[var(--color-text-muted)]">
                {reference.page_number && (
                  <span className="flex items-center gap-1">
                    <Hash className="w-3 h-3" /> Page {reference.page_number}
                  </span>
                )}
                {reference.chunk_index !== undefined && (
                  <span>Chunk #{reference.chunk_index}</span>
                )}
              </div>
            </div>
          </div>
          <button onClick={onClose}
            className="p-2 hover:bg-[var(--color-bg-secondary)] rounded-xl
                     text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]
                     transition-colors ml-2">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div>
            <div className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase
                          tracking-wider mb-2 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5" /> 参考内容
            </div>
            <div className="text-sm text-[var(--color-text-secondary)] leading-relaxed
                          whitespace-pre-wrap bg-[var(--color-bg-tertiary)]
                          rounded-xl p-4 border border-[var(--color-border)]">
              {reference.content}
            </div>
          </div>

          <div className={`p-3 rounded-xl border ${scoreColors.bg}`}>
            <div className="text-[11px] font-semibold text-[var(--color-text-muted)] mb-2">
              置信度分析
            </div>
            <div className="flex items-center gap-3 mb-2">
              <div className="flex-1 h-2 bg-[var(--color-bg-secondary)] rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${scoreColors.bar}`}
                  style={{ width: `${scorePercent}%` }}
                />
              </div>
              <span className={`text-sm font-bold ${scoreColors.text}`}>{scorePercent}%</span>
            </div>
            <div className="flex items-center gap-4 text-[10px] text-[var(--color-text-secondary)]">
              {reference.vector_score !== undefined && (
                <span>向量: {Math.round(reference.vector_score * 100)}%</span>
              )}
              {reference.bm25_score !== undefined && reference.bm25_score !== null && (
                <span>BM25: {reference.bm25_score.toFixed(1)}</span>
              )}
              <span className="text-[var(--color-text-muted)]">{getScoreTypeLabel()}</span>
            </div>
          </div>

          <div className="p-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-tertiary)]">
            <div className="text-[11px] font-semibold text-[var(--color-text-muted)] mb-2">
              溯源链路
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="px-2 py-1 rounded bg-blue-100 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300">
                用户提问
              </span>
              <ArrowRight className="w-3 h-3 text-[var(--color-text-muted)]" />
              <span className="px-2 py-1 rounded bg-purple-100 text-purple-700 dark:bg-purple-950/30 dark:text-purple-300">
                Chunk #{reference.chunk_index ?? '?'}
              </span>
              {reference.parent_chunk_index && (
                <>
                  <ArrowRight className="w-3 h-3 text-[var(--color-text-muted)]" />
                  <span className="px-2 py-1 rounded bg-orange-100 text-orange-700 dark:bg-orange-950/30 dark:text-orange-300">
                    Parent
                  </span>
                </>
              )}
              <ArrowRight className="w-3 h-3 text-[var(--color-text-muted)]" />
              <span className="px-2 py-1 rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
                原文
              </span>
            </div>
          </div>

          {onRate && (
            <div className="flex items-center justify-center gap-3 pt-2">
              <span className="text-xs text-[var(--color-text-muted)]">此引用有帮助吗？</span>
              <button
                onClick={() => onRate(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium
                         bg-emerald-50 hover:bg-emerald-100 text-emerald-700
                         dark:bg-emerald-950/30 dark:hover:bg-emerald-950/50 dark:text-emerald-300
                         rounded-lg border border-emerald-200 dark:border-emerald-800
                         transition-colors"
              >
                <ThumbsUp className="w-3.5 h-3.5" /> 有帮助
              </button>
              <button
                onClick={() => onRate(false)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium
                         bg-red-50 hover:bg-red-100 text-red-700
                         dark:bg-red-950/30 dark:hover:bg-red-950/50 dark:text-red-300
                         rounded-lg border border-red-200 dark:border-red-800
                         transition-colors"
              >
                <ThumbsDown className="w-3.5 h-3.5" /> 无帮助
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}