import { format } from 'date-fns'

export default function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="mb-6 animate-fade-up">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-4xl font-light tracking-wide text-ink leading-none"
            style={{ fontFamily: 'var(--font-cormorant)' }}>
            {title}
          </h1>
          {subtitle && <p className="text-xs text-ink-faint mt-2 tracking-wide">{subtitle}</p>}
        </div>
        <p className="text-[10px] text-ink-faint font-mono tracking-widest uppercase">
          {format(new Date(), 'EEE d MMM yyyy · HH:mm')} UTC
        </p>
      </div>
      <div className="gold-rule mt-5" />
    </header>
  )
}
