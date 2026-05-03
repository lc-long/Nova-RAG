import { ExternalLink, FileText } from 'lucide-react'
import type { Reference } from '../../types'

interface SourceCardProps {
  reference: Reference
  onClick: () => void
}

export function SourceCard({ reference, onClick }: SourceCardProps) {
  const truncatedContent = reference.content.slice(0, 60)

  return (
    <button
      onClick={onClick}
      className="group flex items-start gap-2.5 p-3 rounded-xl border border-[var(--color-border)]
                 bg-[var(--color-bg-secondary)] hover:bg-[var(--color-bg-tertiary)]
                 hover:border-[var(--color-accent)]/30 text-left w-56 shrink-0
                 transition-all duration-150 cursor-pointer shadow-sm hover:shadow-md"
    >
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
    </button>
  )
}