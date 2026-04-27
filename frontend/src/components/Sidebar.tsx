import { useState } from 'react'
import { Upload, FileText, Trash2, BookOpen } from 'lucide-react'

interface SidebarProps {
  currentDoc: string | null
  onSelectDoc: (doc: string) => void
}

interface Document {
  id: string
  name: string
  size: string
  date: string
}

const mockDocs: Document[] = [
  { id: '1', name: '员工手册.pdf', size: '2.3MB', date: '2026-04-20' },
  { id: '2', name: '报销流程.md', size: '156KB', date: '2026-04-18' },
  { id: '3', name: '技术方案.docx', size: '890KB', date: '2026-04-15' },
]

export default function Sidebar({ currentDoc, onSelectDoc }: SidebarProps) {
  const [docs, setDocs] = useState<Document[]>(mockDocs)
  const [uploading, setUploading] = useState(false)

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    // Stub for Go backend upload
    setTimeout(() => {
      const newDoc: Document = {
        id: Date.now().toString(),
        name: file.name,
        size: `${(file.size / 1024).toFixed(0)}KB`,
        date: new Date().toISOString().split('T')[0],
      }
      setDocs(prev => [newDoc, ...prev])
      setUploading(false)
    }, 1500)
  }

  return (
    <aside className="w-72 bg-white border-r border-gray-200 flex flex-col h-full">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-2 mb-4">
          <BookOpen className="w-6 h-6 text-indigo-600" />
          <span className="font-semibold text-gray-900">Lumina Insight</span>
        </div>

        <label className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg cursor-pointer transition-colors">
          <Upload className="w-4 h-4" />
          <span className="text-sm font-medium">{uploading ? '上传中...' : '上传文档'}</span>
          <input
            type="file"
            accept=".pdf,.md,.docx"
            className="hidden"
            onChange={handleUpload}
            disabled={uploading}
          />
        </label>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          文档列表
        </h3>
        <div className="space-y-2">
          {docs.map(doc => (
            <div
              key={doc.id}
              onClick={() => onSelectDoc(doc.id)}
              className={`group flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${
                currentDoc === doc.id
                  ? 'bg-indigo-50 border border-indigo-200'
                  : 'hover:bg-gray-100'
              }`}
            >
              <FileText className="w-5 h-5 text-gray-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{doc.name}</p>
                <p className="text-xs text-gray-500">{doc.size}</p>
              </div>
              <button className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 rounded transition-opacity">
                <Trash2 className="w-4 h-4 text-gray-400" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </aside>
  )
}