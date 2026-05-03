import type { Reference } from '../../types'

interface CitationBadgeProps {
  index: number
  onClick: () => void
  reference?: Reference
}

export function CitationBadge({ index, onClick, reference }: CitationBadgeProps) {
  const score = reference?.score ?? 0
  const scorePercent = Math.round(score * 100)

  const getScoreColor = () => {
    if (score >= 0.8) return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300 border-emerald-300'
    if (score >= 0.6) return 'bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300 border-amber-300'
    return 'bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-300 border-red-300'
  }

  return (
    <sup
      onClick={(e) => { e.stopPropagation(); onClick() }}
      className={`cursor-pointer text-[11px] px-1.5 py-0.5 mx-0.5 font-semibold transition-all duration-150
                 select-none inline-flex items-center justify-center border rounded
                 hover:scale-105 active:scale-95 ${getScoreColor()}`}
      style={{ fontFeatureSettings: '"tnum"' }}
      title={`置信度: ${scorePercent}%`}
    >
      {index}
    </sup>
  )
}