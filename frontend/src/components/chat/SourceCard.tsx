import { ExternalLink, FileText, ThumbsUp, ThumbsDown } from 'lucide-react'
import type { Reference } from '../../types'

interface SourceCardProps {
  reference: Reference
  onClick: () => void
  onRate?: (helpful: boolean) => void
  showRating?: boolean
}

export function SourceCard({ reference, onClick, onRate, showRating = false }: SourceCardProps) {
  const truncatedContent = reference.content.slice(0, 60)
  const score = reference.score ?? 0.5
  const scorePercent = Math.round(score * 100)

  const getScoreColor = () => {
    if (score >= 0.8) return 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/30 dark:text-emerald-400'
    if (score >= 0.6) return 'text-amber-600 bg-amber-50 dark:bg-amber-950/30 dark:text-amber-400'
    return 'text-red-600 bg-red-50 dark:bg-red-950/30 dark:text-red-400'
  }

  const getScoreLabel = () => {
    if (reference.score_type === 'rerank') return '重排'
    if (reference.score_type === 'vector') return '向量'
    if (reference.score_type === 'bm25') return '关键词'
    return '混合'
  }

  return (
    <div className="group flex flex-col gap-2 p-3 rounded-xl border border-[var(--color-border)]
                   bg-[var(--color-bg-secondary)] hover:bg-[var(--color-bg-tertiary)]
                   hover:border-[var(--color-accent)]/30 text-left w-56 shrink-0
                   transition-all duration-150 cursor-pointer shadow-sm hover:shadow-md"
         onClick={onClick}>
      <div className="flex items-start gap-2.5">
        <div className="shrink-0 w-7 h-7 rounded-lg bg-[var(--color-accent-soft)]
                      flex items-center justify-center
                      border border-[var(--color-accent)]/20">
          <span className="text-[11px] font-bold text-[var(--color-accent)]">
            {reference.index}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <FileText className="w-3 h-3 text-[var(--color-text-muted)] shrink-0" />
            <span className="text-[10px] font-medium text-[var(--color-text-muted)] truncate">
              {reference.doc_id.length > 16 ? `${reference.doc_id.slice(0, 16)}...` : reference.doc_id}
            </span>
          </div>
          <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed line-clamp-2">
            {truncatedContent}...
          </p>
        </div>
        <ExternalLink className="w-3.5 h-3.5 text-[var(--color-text-muted)] shrink-0
                                 opacity-0 group-hover:opacity-100 transition-opacity mt-0.5" />
      </div>

      <div className="flex items-center justify-between">
        <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${getScoreColor()}`}>
          <span>{scorePercent}%</span>
          <span className="opacity-60">{getScoreLabel()}</span>
        </div>
        {showRating && onRate && (
          <div className="flex items-center gap-1">
            <button
              onClick={(e) => { e.stopPropagation(); onRate(true) }}
              className="p-1 hover:bg-emerald-100 dark:hover:bg-emerald-950/30 rounded transition-colors"
              title="有帮助"
            >
              <ThumbsUp className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onRate(false) }}
              className="p-1 hover:bg-red-100 dark:hover:bg-red-950/30 rounded transition-colors"
              title="无帮助"
            >
              <ThumbsDown className="w-3 h-3 text-red-600 dark:text-red-400" />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}