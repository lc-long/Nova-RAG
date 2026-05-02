import { FileText, X } from 'lucide-react'
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
    <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200
                    rounded-xl shadow-lg max-h-48 overflow-y-auto z-20">
      <div className="p-2 text-xs text-gray-400 font-medium border-b border-gray-100">选择文档进行精准检索</div>
      {filtered.map(doc => (
        <button
          key={doc.id}
          onClick={() => onSelect(doc)}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left
                     hover:bg-indigo-50 transition-colors"
        >
          <FileText className="w-4 h-4 text-gray-400 shrink-0" />
          <span className="truncate text-gray-700">{doc.name}</span>
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
    <div className="flex flex-wrap gap-1.5 mb-2">
      {docIds.map(docId => {
        const doc = docs.find(d => d.id === docId)
        return (
          <span key={docId} className="inline-flex items-center gap-1 px-2 py-1 bg-indigo-50 text-indigo-700
                                        text-xs font-medium rounded-full border border-indigo-200">
            <FileText className="w-3 h-3" />
            <span className="max-w-[120px] truncate">{doc?.name || docId.slice(0, 8)}</span>
            <button type="button" onClick={() => onRemove(docId)} className="hover:text-red-500 transition-colors">
              <X className="w-3 h-3" />
            </button>
          </span>
        )
      })}
    </div>
  )
}
