interface CitationBadgeProps {
  index: number
  onClick: () => void
}

export function CitationBadge({ index, onClick }: CitationBadgeProps) {
  return (
    <sup
      onClick={(e) => { e.stopPropagation(); onClick() }}
      className="cursor-pointer text-[11px] bg-[var(--color-accent-soft)] text-[var(--color-accent)]
                 hover:bg-[var(--color-accent)] hover:text-white
                 rounded px-1.5 py-0.5 mx-0.5 font-semibold transition-all duration-150
                 select-none inline-flex items-center justify-center
                 border border-transparent hover:border-[var(--color-accent)]
                 shadow-sm hover:shadow"
      style={{ fontFeatureSettings: '"tnum"' }}
    >
      {index}
    </sup>
  )
}