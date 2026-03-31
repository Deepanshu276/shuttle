interface SummaryCardProps {
  label: string
  value: string
  helper?: string
}

export function SummaryCard({ label, value, helper }: SummaryCardProps) {
  return (
    <article className="summary-card">
      <p className="summary-card__label">{label}</p>
      <strong className="summary-card__value">{value}</strong>
      {helper ? <p className="summary-card__helper">{helper}</p> : null}
    </article>
  )
}
