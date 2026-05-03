import { Sun, Moon, Monitor } from 'lucide-react'
import { useTheme, type Theme } from '../contexts/ThemeContext'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  const options: { value: Theme; icon: typeof Sun; label: string }[] = [
    { value: 'light', icon: Sun, label: 'Light' },
    { value: 'dark', icon: Moon, label: 'Dark' },
    { value: 'system', icon: Monitor, label: 'System' },
  ]

  return (
    <div className="flex items-center gap-0.5 p-1 bg-[var(--color-bg-tertiary)] rounded-lg">
      {options.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          title={label}
          className={`p-1.5 rounded-md transition-all duration-150 ${
            theme === value
              ? 'bg-[var(--color-bg-elevated)] shadow-sm text-[var(--color-accent)]'
              : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
          }`}
        >
          <Icon className="w-4 h-4" />
        </button>
      ))}
    </div>
  )
}