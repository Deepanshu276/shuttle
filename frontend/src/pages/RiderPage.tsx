import { useEffect, useMemo, useState, type FormEvent } from 'react'

import { api } from '../api'
import { MapView } from '../components/MapView'
import { StatusPill } from '../components/StatusPill'
import { SummaryCard } from '../components/SummaryCard'
import type { DashboardSummary, RideRequest, Route, StopsCatalog, Vehicle } from '../types'

function formatLocalDateTimeInput(date: Date) {
  const pad = (value: number) => value.toString().padStart(2, '0')

  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`
}

function nextCommuteWindow() {
  const now = new Date()
  const nextSlot = new Date(now)
  nextSlot.setHours(9, 0, 0, 0)

  if (nextSlot <= now) {
    nextSlot.setDate(nextSlot.getDate() + 1)
  }

  return formatLocalDateTimeInput(nextSlot)
}

function formatClock(value?: string | null) {
  if (!value) {
    return 'Not scheduled'
  }

  return new Date(value).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function estimatePickupWait(
  pickupStopId: string,
  stopsCatalog: StopsCatalog | null,
  vehicles: Vehicle[],
  summary: DashboardSummary | null,
) {
  if (!stopsCatalog || pickupStopId === '') {
    return 8
  }

  const stop = stopsCatalog.pickups.find((item) => item.id === pickupStopId)
  if (!stop || vehicles.length === 0) {
    return summary?.average_wait_minutes || 8
  }

  const nearestVehicleDistance = Math.min(
    ...vehicles.map((vehicle) => {
      const latDelta = vehicle.current_latitude - stop.latitude
      const lngDelta = vehicle.current_longitude - stop.longitude
      return Math.sqrt(latDelta * latDelta + lngDelta * lngDelta)
    }),
  )

  const demandPressure = Math.max((summary?.active_requests || 0) - vehicles.length, 0)
  return Math.round(Math.max(5, nearestVehicleDistance * 120 + demandPressure * 2 + 5))
}

export function RiderPage() {
  const [stopsCatalog, setStopsCatalog] = useState<StopsCatalog | null>(null)
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [routes, setRoutes] = useState<Route[]>([])
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [activeRequest, setActiveRequest] = useState<RideRequest | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({
    rider_name: '',
    rider_team: '',
    pickup_stop_id: '',
    destination_stop_id: '',
    desired_arrival_at: nextCommuteWindow(),
    passenger_count: 1,
  })

  useEffect(() => {
    let active = true

    const loadStaticData = async () => {
      try {
        const [stops, nextVehicles, nextRoutes, nextSummary] = await Promise.all([
          api.getStops(),
          api.getVehicles(),
          api.getRoutes(),
          api.getSummary(),
        ])

        if (!active) {
          return
        }

        setStopsCatalog(stops)
        setVehicles(nextVehicles)
        setRoutes(nextRoutes)
        setSummary(nextSummary)
        setForm((current) => ({
          ...current,
          pickup_stop_id: current.pickup_stop_id || stops.pickups[0]?.id || '',
          destination_stop_id: current.destination_stop_id || stops.destinations[0]?.id || '',
        }))
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : 'Unable to load the shuttle map.')
        }
      }
    }

    void loadStaticData()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    const interval = window.setInterval(() => {
      void Promise.all([api.getVehicles(), api.getRoutes(), api.getSummary()])
        .then(([nextVehicles, nextRoutes, nextSummary]) => {
          setVehicles(nextVehicles)
          setRoutes(nextRoutes)
          setSummary(nextSummary)
        })
        .catch((pollError) => {
          setError(pollError instanceof Error ? pollError.message : 'Unable to refresh live view.')
        })
    }, 5000)

    return () => window.clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!activeRequest?.id) {
      return
    }

    const interval = window.setInterval(() => {
      void api
        .getRequest(activeRequest.id)
        .then((nextRequest) => {
          setActiveRequest(nextRequest)
        })
        .catch((pollError) => {
          setError(pollError instanceof Error ? pollError.message : 'Unable to refresh trip status.')
        })
    }, 4000)

    return () => window.clearInterval(interval)
  }, [activeRequest?.id])

  const estimatedWait = useMemo(
    () => estimatePickupWait(form.pickup_stop_id, stopsCatalog, vehicles, summary),
    [form.pickup_stop_id, stopsCatalog, vehicles, summary],
  )

  const allStops = stopsCatalog ? [...stopsCatalog.pickups, ...stopsCatalog.destinations] : []

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    setMessage(null)

    try {
      const createdRequest = await api.createRequest({
        rider_name: form.rider_name.trim(),
        rider_team: form.rider_team.trim() || undefined,
        pickup_stop_id: form.pickup_stop_id,
        destination_stop_id: form.destination_stop_id,
        desired_arrival_at: form.desired_arrival_at,
        passenger_count: form.passenger_count,
      })

      await api.runDispatch()

      const refreshedRequest = await api.getRequest(createdRequest.id)
      const [nextVehicles, nextRoutes, nextSummary] = await Promise.all([
        api.getVehicles(),
        api.getRoutes(),
        api.getSummary(),
      ])

      setActiveRequest(refreshedRequest)
      setVehicles(nextVehicles)
      setRoutes(nextRoutes)
      setSummary(nextSummary)
      setMessage('Ride booked and included in the latest pooling cycle.')
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to submit the shuttle request.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-grid">
      <section className="panel panel--form">
        <div className="panel__header">
          <div>
            <p className="eyebrow">Rider flow</p>
            <h2>Book your campus shuttle</h2>
          </div>
          <p className="panel__lede">
            Request a pooled van for the morning inbound commute and get a live ETA as demand is matched.
          </p>
        </div>

        <div className="summary-grid summary-grid--three">
          <SummaryCard
            label="Estimated pickup"
            value={`${estimatedWait} min`}
            helper="Calculated from nearby van positions and current demand."
          />
          <SummaryCard
            label="Pooling cycle"
            value="Every 1-2 min"
            helper="New requests are batched into the next routing pass."
          />
          <SummaryCard
            label="Campus window"
            value="Morning inbound"
            helper="Seeded for a single business park commute."
          />
        </div>

        <form className="booking-form" onSubmit={handleSubmit}>
          <label>
            <span>Name</span>
            <input
              required
              value={form.rider_name}
              onChange={(event) => setForm((current) => ({ ...current, rider_name: event.target.value }))}
              placeholder="Enter employee name"
            />
          </label>

          <label>
            <span>Team</span>
            <input
              value={form.rider_team}
              onChange={(event) => setForm((current) => ({ ...current, rider_team: event.target.value }))}
              placeholder="Engineering, Finance, HR..."
            />
          </label>

          <label>
            <span>Pickup zone</span>
            <select
              required
              value={form.pickup_stop_id}
              onChange={(event) => setForm((current) => ({ ...current, pickup_stop_id: event.target.value }))}
            >
              {stopsCatalog?.pickups.map((stop) => (
                <option key={stop.id} value={stop.id}>
                  {stop.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Destination</span>
            <select
              required
              value={form.destination_stop_id}
              onChange={(event) =>
                setForm((current) => ({ ...current, destination_stop_id: event.target.value }))
              }
            >
              {stopsCatalog?.destinations.map((stop) => (
                <option key={stop.id} value={stop.id}>
                  {stop.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Desired arrival</span>
            <input
              required
              type="datetime-local"
              value={form.desired_arrival_at}
              onChange={(event) =>
                setForm((current) => ({ ...current, desired_arrival_at: event.target.value }))
              }
            />
          </label>

          <label>
            <span>Seats</span>
            <input
              required
              min={1}
              max={4}
              type="number"
              value={form.passenger_count}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  passenger_count: Number(event.target.value),
                }))
              }
            />
          </label>

          <button className="button button--primary" type="submit" disabled={submitting}>
            {submitting ? 'Booking ride...' : 'Request pooled van'}
          </button>
        </form>

        {message ? <p className="notice notice--success">{message}</p> : null}
        {error ? <p className="notice notice--error">{error}</p> : null}
      </section>

      <section className="panel panel--status">
        <div className="panel__header">
          <div>
            <p className="eyebrow">Live trip state</p>
            <h2>Current rider update</h2>
          </div>
        </div>

        {activeRequest ? (
          <article className="trip-card">
            <div className="trip-card__title">
              <div>
                <h3>{activeRequest.rider_name}</h3>
                <p>
                  {activeRequest.pickup_stop_name} to {activeRequest.destination_stop_name}
                </p>
              </div>
              <StatusPill status={activeRequest.live_status} />
            </div>

            <div className="summary-grid summary-grid--two">
              <SummaryCard
                label="Assigned van"
                value={activeRequest.assigned_vehicle_name ?? 'Queued'}
                helper="Updated from each routing pass."
              />
              <SummaryCard
                label="Pickup ETA"
                value={
                  activeRequest.pickup_eta_minutes
                    ? `${activeRequest.pickup_eta_minutes} min`
                    : 'Awaiting match'
                }
                helper={`Target arrival ${formatClock(activeRequest.desired_arrival_at)}`}
              />
            </div>

            <div className="trip-card__meta">
              <div>
                <span>Destination ETA</span>
                <strong>
                  {activeRequest.destination_eta_minutes
                    ? `${activeRequest.destination_eta_minutes} min`
                    : 'TBD'}
                </strong>
              </div>
              <div>
                <span>Route progress</span>
                <strong>{Math.round(activeRequest.route_progress * 100)}%</strong>
              </div>
            </div>
          </article>
        ) : (
          <div className="empty-state">
            <h3>No active rider request yet</h3>
            <p>Book a commute above to see the matching state, ETA, and assigned van update live.</p>
          </div>
        )}

        <MapView stops={allStops} routes={routes} vehicles={vehicles} title="Rider live map" />
      </section>
    </div>
  )
}
