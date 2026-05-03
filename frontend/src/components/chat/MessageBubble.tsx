import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, ChevronUp, BrainCircuit, Search, Sparkles } from 'lucide-react'
import type { Message } from '../../types'
import { CitationBadge } from './CitationBadge'

interface MessageBubbleProps {
  msg: Message
  onCite: (index: number) => void
}

export function MessageBubble({ msg, onCite }: MessageBubbleProps) {
  if (msg.role === 'user') {
    return (
      <div className="inline-block px-4 py-3 rounded-2xl rounded-br-md
                     bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-sm">
        <div className="prose prose-sm max-w-none text-white whitespace-pre-wrap
                      prose-custom [&_a]:text-indigo-200 [&_a]:hover:text-white">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
        </div>
      </div>
    )
  }

  const isStreaming = msg.reasoning && !msg.content
  const isThinking = msg.thoughts.length > 0 && !msg.content

  const refMap = new Map(msg.references?.map(r => [r.index, r]) ?? [])

  return (
    <div className="space-y-2.5 max-w-xl">
      <ThoughtPanel thoughts={msg.thoughts} isStreaming={isThinking} />
      {msg.reasoning && (
        <ReasoningPanel reasoning={msg.reasoning} isStreaming={!!isStreaming} />
      )}
      {msg.content && (
        <div className="inline-block px-4 py-3 rounded-2xl rounded-bl-md
                       bg-[var(--color-bg-secondary)] shadow-sm
                       border border-[var(--color-border)]
                       text-[var(--color-text-primary)]">
          <div className="prose prose-sm max-w-none text-[var(--color-text-primary)] whitespace-pre-wrap
                        leading-relaxed prose-custom
                        [&_a]:text-[var(--color-accent)] [&_a]:hover:text-[var(--color-accent-hover)]">
            {renderWithCitations(msg.content, onCite, refMap)}
          </div>
        </div>
      )}
    </div>
  )
}

function renderWithCitations(
  text: string,
  onCite: (index: number) => void,
  refMap: Map<number, import('../../types').Reference>
): React.ReactNode {
  const parts = text.split(/(\[\d+\])/g)
  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/)
    if (match) {
      const idx = parseInt(match[1])
      return <CitationBadge key={i} index={idx} onClick={() => onCite(idx)} reference={refMap.get(idx)} />
    }
    return <span key={i}>{part}</span>
  })
}

function ThoughtPanel({ thoughts, isStreaming }: { thoughts: string[]; isStreaming: boolean }) {
  const [open, setOpen] = useState(isStreaming)
  if (thoughts.length === 0) return null

  return (
    <div className="mb-1">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 px-3 py-2 cursor-pointer select-none
                   text-[var(--color-text-muted)] hover:text-[var(--color-accent)]
                   hover:bg-[var(--color-bg-tertiary)] rounded-lg text-xs font-medium
                   transition-colors duration-150 group"
      >
        <Search className="w-3.5 h-3.5 text-[var(--color-accent)] group-hover:scale-110 transition-transform" />
        {open || isStreaming
          ? <ChevronUp className="w-3.5 h-3.5" />
          : <ChevronDown className="w-3.5 h-3.5" />}
        <span className="text-[var(--color-text-secondary)]">检索与推理过程</span>
        {isStreaming && (
          <span className="ml-1.5 flex items-center gap-1">
            <span className="w-1.5 h-1.5 bg-[var(--color-accent)] rounded-full animate-pulse" />
            <span className="text-[var(--color-accent)]">检索中...</span>
          </span>
        )}
        {thoughts.length > 0 && (
          <span className="ml-auto text-[10px] bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">
            {thoughts.length} 步
          </span>
        )}
      </button>
      {(open || isStreaming) && (
        <div className="mt-1 ml-2 px-3 py-2.5 text-xs text-[var(--color-text-secondary)]
                      bg-[var(--color-bg-tertiary)] rounded-lg border border-[var(--color-border)]
                      space-y-1.5 max-h-48 overflow-y-auto">
          {thoughts.map((t, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="shrink-0 w-4 h-4 rounded-full bg-[var(--color-accent)]/10
                             text-[var(--color-accent)] text-[10px] font-bold
                             flex items-center justify-center mt-0.5">
                {i + 1}
              </span>
              <span className="leading-relaxed">{t}</span>
            </div>
          ))}
          {isStreaming && (
            <div className="flex items-center gap-2 text-[var(--color-text-muted)] pt-1">
              <span className="typing-dot w-1.5 h-1.5 bg-[var(--color-text-muted)] rounded-full" />
              <span className="typing-dot w-1.5 h-1.5 bg-[var(--color-text-muted)] rounded-full" style={{ animationDelay: '200ms' }} />
              <span className="typing-dot w-1.5 h-1.5 bg-[var(--color-text-muted)] rounded-full" style={{ animationDelay: '400ms' }} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ReasoningPanel({ reasoning, isStreaming }: { reasoning: string; isStreaming: boolean }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg overflow-hidden">
      <button
        type="button"
        className="flex items-center gap-2 w-full px-3 py-2.5 cursor-pointer select-none
                   text-[var(--color-text-secondary)] hover:text-[var(--color-accent)]
                   hover:bg-[var(--color-bg-secondary)] text-sm font-medium
                   transition-colors duration-150"
        onClick={() => setOpen(o => !o)}
      >
        <BrainCircuit className="w-4 h-4 text-[var(--color-accent)]" />
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        <span>AI 思考过程</span>
        {isStreaming && (
          <span className="ml-auto flex items-center gap-1 text-xs animate-pulse text-[var(--color-accent)]">
            <Sparkles className="w-3 h-3" /> 生成中...
          </span>
        )}
      </button>
      {open && (
        <div className="px-4 py-3 text-sm text-[var(--color-text-secondary)]
                      whitespace-pre-wrap leading-relaxed
                      bg-[var(--color-bg-secondary)] border-t border-[var(--color-border)]">
          {reasoning}
        </div>
      )}
    </div>
  )
}