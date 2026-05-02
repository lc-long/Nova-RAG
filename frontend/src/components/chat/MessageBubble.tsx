import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { Message } from '../../types'
import { CitationBadge } from './CitationBadge'

interface MessageBubbleProps {
  msg: Message
  onCite: (index: number) => void
}

export function MessageBubble({ msg, onCite }: MessageBubbleProps) {
  if (msg.role === 'user') {
    return (
      <div className="inline-block p-4 rounded-2xl bg-indigo-600 text-white max-w-xl">
        <div className="prose prose-sm max-w-none text-white whitespace-pre-wrap">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
        </div>
      </div>
    )
  }

  const isStreaming = msg.reasoning && !msg.content
  const isThinking = msg.thoughts.length > 0 && !msg.content

  return (
    <div className="space-y-2 max-w-xl">
      <ThoughtPanel thoughts={msg.thoughts} isStreaming={isThinking} />
      {msg.reasoning && (
        <ReasoningPanel reasoning={msg.reasoning} isStreaming={!!isStreaming} />
      )}
      {msg.content && (
        <div className="inline-block p-4 rounded-2xl bg-white shadow-sm border border-gray-200 text-gray-800 max-w-xl">
          <div className="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap leading-relaxed">
            {renderWithCitations(msg.content, onCite)}
          </div>
        </div>
      )}
    </div>
  )
}

function renderWithCitations(text: string, onCite: (index: number) => void): React.ReactNode {
  const parts = text.split(/(\[\d+\])/g)
  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/)
    if (match) return <CitationBadge key={i} index={parseInt(match[1])} onClick={() => onCite(parseInt(match[1]))} />
    return <span key={i}>{part}</span>
  })
}

function ThoughtPanel({ thoughts, isStreaming }: { thoughts: string[]; isStreaming: boolean }) {
  const [open, setOpen] = useState(isStreaming)
  if (thoughts.length === 0) return null

  return (
    <div className="mb-2">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 px-3 py-2 cursor-pointer select-none text-gray-400
                   hover:bg-gray-100 rounded-lg text-xs font-medium transition-colors"
      >
        {open || isStreaming ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        <span>检索与推理过程</span>
        {isStreaming && <span className="ml-1 w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />}
      </button>
      {(open || isStreaming) && (
        <div className="mt-1 px-3 py-2 text-xs text-gray-500 bg-gray-50 rounded-lg border border-gray-100 space-y-1">
          {thoughts.map((t, i) => (
            <div key={i} className="flex items-start gap-1.5">
              <span className="shrink-0 mt-0.5">·</span>
              <span>{t}</span>
            </div>
          ))}
          {isStreaming && <span className="inline-block w-2 h-3 bg-gray-400 animate-pulse rounded-sm" />}
        </div>
      )}
    </div>
  )
}

function ReasoningPanel({ reasoning, isStreaming }: { reasoning: string; isStreaming: boolean }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg">
      <button
        type="button"
        className="flex items-center gap-2 w-full px-3 py-2 cursor-pointer select-none text-gray-500 hover:bg-gray-100 text-sm font-medium"
        onClick={() => setOpen(o => !o)}
      >
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        <span>AI 思考过程</span>
        {isStreaming && <span className="ml-2 text-xs animate-pulse">（生成中...）</span>}
      </button>
      {open && (
        <div className="px-4 py-2 text-sm text-gray-600 whitespace-pre-wrap bg-gray-50 border-t border-gray-100">
          {reasoning}
        </div>
      )}
    </div>
  )
}
