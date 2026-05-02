import { useEffect } from 'react'
import { X } from 'lucide-react'
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />
      <div onClick={(e) => e.stopPropagation()}
        className="relative bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[70vh]
                   flex flex-col overflow-hidden border border-gray-200">
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-lg">📄</span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-gray-800 truncate">{reference.doc_id}</p>
              {reference.page_number ? <p className="text-xs text-gray-400">Page {reference.page_number}</p> : null}
            </div>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          <div className="text-xs font-bold text-blue-500 mb-2">Source [{reference.index}]</div>
          <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap bg-gray-50
                          rounded-lg p-4 border border-gray-100">
            {reference.content}
          </div>
        </div>
      </div>
    </div>
  )
}
