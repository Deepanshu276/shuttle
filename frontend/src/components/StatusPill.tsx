import type { RequestStatus, RouteStatus, VehicleStatus } from '../types'

type StatusValue = RequestStatus | RouteStatus | VehicleStatus

const toneByStatus: Record<StatusValue, string> = {
  requested: 'neutral',
  matched: 'success',
  arriving: 'info',
  onboard: 'accent',
  dropped: 'muted',
  planned: 'neutral',
  active: 'success',
  completed: 'muted',
  idle: 'muted',
  assigned: 'info',
  en_route: 'accent',
}

interface StatusPillProps {
  status: StatusValue
  label?: string
}

export function StatusPill({ status, label }: StatusPillProps) {
  const tone = toneByStatus[status]

  return (
    <span className={`status-pill status-pill--${tone}`}>
      {label ?? status.replace('_', ' ')}
    </span>
  )
}
