'use client'

interface KpiCardProps {
  label: string
  value: number | null
  unit?: string
  delay?: number
}

export default function KpiCard({ label, value, unit, delay = 0 }: KpiCardProps) {
  return (
    <div
      className="card-gold p-5 flex flex-col gap-3 animate-fade-up"
      style={{ animationDelay: `${delay}ms` }}
    >
      <span className="text-xs tracking-[0.2em] uppercase text-gold-dim font-mono">
        {label}
      </span>
      <div className="flex items-end gap-2">
        <span
          className="font-mono text-4xl font-light text-cream leading-none"
          style={{ fontFamily: 'var(--font-dm-mono)' }}
        >
          {value === null ? (
            <span className="text-obsidian-muted animate-pulse">—</span>
          ) : (
            value.toLocaleString()
          )}
        </span>
        {unit && (
          <span className="text-xs text-gold-dim mb-1 tracking-widest">{unit}</span>
        )}
      </div>
    </div>
  )
}
