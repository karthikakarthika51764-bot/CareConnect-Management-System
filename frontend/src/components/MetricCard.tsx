import type { LucideIcon } from 'lucide-react'

type Props = { label: string; value: number | string; note: string; icon: LucideIcon; tone: 'mint' | 'coral' | 'gold' | 'blue' }

export function MetricCard({ label, value, note, icon: Icon, tone }: Props) {
  return (
    <article className={`metric-card metric-${tone}`}>
      <div className="metric-top"><span>{label}</span><span className="metric-icon"><Icon size={18} strokeWidth={1.8} /></span></div>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  )
}
