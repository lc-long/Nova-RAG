import { FileText, Search } from 'lucide-react'
import type { DocItem } from '../../types'

interface MentionPopoverProps {
  docs: DocItem[]
  filter: string
  onSelect: (doc: DocItem) => void
}

export function MentionPopover({ docs, filter, onSelect }: MentionPopoverProps) {
  const filtered = docs.filter(d => d.name.toLowerCase().includes(filter.toLowerCase()))
  if (filtered.length === 0) return null

  return (
    <div className="absolute bottom-full left-0 right-0 mb-2.5
                    bg-[var(--color-bg-secondary)] border border-[var(--color-border)]
                    rounded-xl shadow-lg max-h-56 overflow-y-auto z-20
                    animate-slide-up">
      <div className="px-3 py-2 text-[11px] font-semibold text-[var(--color-text-muted)]
                    border-b border-[var(--color-border)] flex items-center gap-1.5
                    bg-[var(--color-bg-tertiary)] rounded-t-xl">
        <Search className="w-3.5 h-3.5" />
        选择文档进行精准检索
      </div>
      {filtered.map((doc, idx) => (
        <button
          key={doc.id}
          onClick={() => onSelect(doc)}
          className="w-full flex items-center gap-2.5 px-3 py-2.5 text-sm text-left
                     hover:bg-[var(--color-accent-soft)] transition-colors duration-150
                     border-b border-[var(--color-border)] last:border-0"
          style={{ animationDelay: `${idx * 20}ms` }}
        >
          <FileText className="w-4 h-4 text-[var(--color-text-muted)] shrink-0" />
          <span className="truncate text-[var(--color-text-primary)] font-medium">{doc.name}</span>
          {doc.status && (
            <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded-full ${
              doc.status === 'ready'
                ? 'bg-emerald-50 text-emerald-600'
                : doc.status === 'processing'
                ? 'bg-amber-50 text-amber-600'
                : 'bg-red-50 text-red-500'
            }`}>
              {doc.status === 'ready' ? '就绪' : doc.status === 'processing' ? '处理中' : '失败'}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}

interface MentionTagsProps {
  docIds: string[]
  docs: DocItem[]
  onRemove: (docId: string) => void
}

export function MentionTags({ docIds, docs, onRemove }: MentionTagsProps) {
  if (docIds.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2 mb-2.5">
      {docIds.map(docId => {
        const doc = docs.find(d => d.id === docId)
        return (
          <span key={docId}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5
                     bg-[var(--color-accent-soft)] text-[var(--color-accent)]
                     text-xs font-medium rounded-lg border border-[var(--color-accent)]/20
                     animate-fade-in">
            <FileText className="w-3 h-3" />
            <span className="max-w-[100px] truncate">{doc?.name || docId.slice(0, 8)}</span>
            <button type="button" onClick={() => onRemove(docId)}
              className="hover:text-red-500 transition-colors p-0.5 rounded
                       hover:bg-red-50 dark:hover:bg-red-950/30">
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none"
                   stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                <path d="M2 2l6 6M8 2l-6 6" />
              </svg>
            </button>
          </span>
        )
      })}
    </div>
  )
}