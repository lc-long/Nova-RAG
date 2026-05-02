import { ExternalLink } from 'lucide-react'
import type { Reference } from '../../types'

interface SourceCardProps {
  reference: Reference
  onClick: () => void
}

export function SourceCard({ reference, onClick }: SourceCardProps) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 p-2 border border-gray-200 rounded-lg
                 bg-gray-50 hover:bg-gray-100 text-sm w-48 shadow-sm
                 transition-all text-left shrink-0"
    >
      <span className="text-base shrink-0">📄</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1">
          <span className="text-[10px] font-bold text-white bg-blue-500 rounded px-1 shrink-0">{reference.index}</span>
          <span className="truncate text-gray-700 font-medium text-xs">{reference.doc_id.slice(0, 8)}...</span>
        </div>
        <p className="text-[11px] text-gray-400 truncate mt-0.5">{reference.content.slice(0, 40)}...</p>
      </div>
      <ExternalLink className="w-3 h-3 text-gray-300 shrink-0" />
    </button>
  )
}
