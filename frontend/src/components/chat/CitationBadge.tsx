interface CitationBadgeProps {
  index: number
  onClick: () => void
}

export function CitationBadge({ index, onClick }: CitationBadgeProps) {
  return (
    <sup
      onClick={(e) => { e.stopPropagation(); onClick() }}
      className="cursor-pointer text-xs bg-blue-50 text-blue-600 hover:bg-blue-100
                 rounded px-1 py-0.5 mx-0.5 font-medium transition-colors select-none"
    >
      {index}
    </sup>
  )
}
