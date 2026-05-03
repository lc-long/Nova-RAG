import { useEffect } from 'react'
import { X, FileText, Hash, Layers } from 'lucide-react'
import type { Reference } from '../../types'

interface SourceModalProps {
  reference: Reference
  onClose: () => void
}

export function SourceModal({ reference, onClose }: SourceModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in"
         onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div onClick={(e) => e.stopPropagation()}
        className="relative bg-[var(--color-bg-secondary)] rounded-2xl shadow-2xl
                   max-w-lg w-full max-h-[75vh] flex flex-col overflow-hidden
                   border border-[var(--color-border)] animate-slide-up">
        <div className="flex items-center justify-between p-4 border-b border-[var(--color-border)]
                       bg-[var(--color-bg-tertiary)]">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-xl bg-[var(--color-accent-soft)] border border-[var(--color-accent)]/20
                          flex items-center justify-center shrink-0">
              <FileText className="w-4 h-4 text-[var(--color-accent)]" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold text-[var(--color-text-primary)] truncate
                             max-w-[200px] sm:max-w-none">
                  {reference.doc_id}
                </p>
                <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded
                                bg-[var(--color-accent-soft)] text-[10px] font-bold
                                text-[var(--color-accent)] border border-[var(--color-accent)]/20">
                  <Layers className="w-3 h-3" /> {reference.index}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                {reference.page_number && (
                  <span className="text-[10px] text-[var(--color-text-muted)] flex items-center gap-1">
                    <Hash className="w-3 h-3" /> Page {reference.page_number}
                  </span>
                )}
                {reference.source_doc && (
                  <span className="text-[10px] text-[var(--color-text-muted)] truncate max-w-[150px]">
                    {reference.source_doc}
                  </span>
                )}
              </div>
            </div>
          </div>
          <button onClick={onClose}
            className="p-2 hover:bg-[var(--color-bg-secondary)] rounded-xl
                     text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]
                     transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          <div className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase
                        tracking-wider mb-2.5 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5" /> 参考内容
          </div>
          <div className="text-sm text-[var(--color-text-secondary)] leading-relaxed
                        whitespace-pre-wrap bg-[var(--color-bg-tertiary)]
                        rounded-xl p-4 border border-[var(--color-border)]">
            {reference.content}
          </div>
        </div>
      </div>
    </div>
  )
}