import { useState } from 'react'
import { ChevronDown, ChevronUp, Search, BarChart2, FileText, Layers, Clock } from 'lucide-react'
import type { Message } from '../../types'

interface RAGMetricsPanelProps {
  msg: Message
}

export function RAGMetricsPanel({ msg }: RAGMetricsPanelProps) {
  const [open, setOpen] = useState(false)

  if (!msg.thoughts || msg.thoughts.length === 0) return null

  const refCount = msg.references?.length || 0
  const docCount = new Set(msg.references?.map(r => r.doc_id) || []).size

  return (
    <div className="bg-[var(--color-bg-tertiary)] border border-[var(--color-border)]
                   rounded-xl overflow-hidden transition-all duration-200">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2.5 px-3.5 py-2.5 cursor-pointer select-none
                   text-[var(--color-text-secondary)] hover:text-[var(--color-accent)]
                   hover:bg-[var(--color-bg-secondary)] transition-colors duration-150"
      >
        <BarChart2 className="w-4 h-4 text-[var(--color-accent)]" />
        <span className="text-xs font-semibold flex-1 text-left">RAG 检索指标</span>
        <div className="flex items-center gap-2 text-[10px] text-[var(--color-text-muted)]">
          <span className="flex items-center gap-1">
            <FileText className="w-3 h-3" />
            {refCount} 来源
          </span>
          <span className="flex items-center gap-1">
            <Layers className="w-3 h-3" />
            {docCount} 文档
          </span>
        </div>
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {open && (
        <div className="px-3.5 pb-3 space-y-2 animate-fade-in">
          <div className="h-px bg-[var(--color-border)]" />

          <div className="grid grid-cols-3 gap-2">
            <MetricCard
              icon={<Search className="w-3.5 h-3.5" />}
              label="检索步骤"
              value={msg.thoughts.length.toString()}
              color="text-blue-500"
            />
            <MetricCard
              icon={<FileText className="w-3.5 h-3.5" />}
              label="参考来源"
              value={refCount.toString()}
              color="text-emerald-500"
            />
            <MetricCard
              icon={<Clock className="w-3.5 h-3.5" />}
              label="来源文档"
              value={docCount.toString()}
              color="text-purple-500"
            />
          </div>

          {msg.references && msg.references.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-[10px] font-semibold text-[var(--color-text-muted)]
                           uppercase tracking-wider px-0.5">
                来源分布
              </div>
              <div className="space-y-1">
                {groupReferencesByDoc(msg.references).map(({ docId, count }) => (
                  <div key={docId} className="flex items-center gap-2">
                    <span className="text-[10px] text-[var(--color-text-muted)] w-24 truncate text-right">
                      {docId.slice(0, 12)}...
                    </span>
                    <div className="flex-1 h-1.5 bg-[var(--color-bg-secondary)] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
                        style={{ width: `${(count / refCount) * 100}%` }}
                      />
                    </div>
                    <span className="text-[10px] font-medium text-[var(--color-text-secondary)] w-6">
                      {count}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="text-[10px] text-[var(--color-text-muted)] bg-[var(--color-bg-secondary)]
                       rounded-lg p-2.5 border border-[var(--color-border)]">
            <div className="font-semibold mb-1.5 text-[var(--color-text-secondary)]">检索策略</div>
            <div className="space-y-1">
              <p>• 混合检索：向量语义 + BM25 关键词</p>
              <p>• RRF 融合排序：权重系数 K=40</p>
              <p>• Cross-encoder 重排序</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function MetricCard({ icon, label, value, color }: {
  icon: React.ReactNode; label: string; value: string; color: string
}) {
  return (
    <div className="flex flex-col items-center gap-1 p-2 bg-[var(--color-bg-secondary)]
                  rounded-lg border border-[var(--color-border)]">
      <div className={color}>{icon}</div>
      <span className="text-sm font-bold text-[var(--color-text-primary)]">{value}</span>
      <span className="text-[10px] text-[var(--color-text-muted)]">{label}</span>
    </div>
  )
}

function groupReferencesByDoc(refs: NonNullable<Message['references']>) {
  const groups: Record<string, number> = {}
  refs.forEach(ref => {
    const docId = ref.source_doc || ref.doc_id
    groups[docId] = (groups[docId] || 0) + 1
  })
  return Object.entries(groups)
    .map(([docId, count]) => ({ docId, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5)
}