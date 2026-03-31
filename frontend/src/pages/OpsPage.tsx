import { useEffect, useMemo, useState } from 'react'

import { api } from '../api'
import { MapView } from '../components/MapView'
import { StatusPill } from '../components/StatusPill'
import { SummaryCard } from '../components/SummaryCard'
import type { DashboardSummary, RideRequest, Route, StopsCatalog, Vehicle } from '../types'

function formatPercentage(value: number) {
  return `${Math.round(value * 100)}%`
}

export function OpsPage() {
  const [stopsCatalog, setStopsCatalog] = useState<StopsCatalog | null>(null)
  const [requests, setRequests] = useState<RideRequest[]>([])
  const [routes, setRoutes] = useState<Route[]>([])
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [banner, setBanner] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busyAction, setBusyAction] = useState<string | null>(null)

  const allStops = useMemo(
    () => (stopsCatalog ? [...stopsCatalog.pickups, ...stopsCatalog.destinations] : []),
    [stopsCatalog],
  )

  async function refresh() {
    const [stops, nextRequests, nextRoutes, nextVehicles, nextSummary] = await Promise.all([
      api.getStops(),
      api.getRequests(),
      api.getRoutes(),
      api.getVehicles(),
      api.getSummary(),
    ])

    setStopsCatalog(stops)
    setRequests(nextRequests)
    setRoutes(nextRoutes)
    setVehicles(nextVehicles)
    setSummary(nextSummary)
  }

  useEffect(() => {
    void refresh().catch((loadError) => {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load the operations dashboard.')
    })
  }, [])

  useEffect(() => {
    const interval = window.setInterval(() => {
      void refresh().catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : 'Unable to refresh operations data.')
      })
    }, 5000)

    return () => window.clearInterval(interval)
  }, [])

  async function runAction(label: string, action: () => Promise<void>) {
    setBusyAction(label)
    setError(null)
    setBanner(null)

    try {
      await action()
      await refresh()
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'Action failed.')
    } finally {
      setBusyAction(null)
    }
  }

  const pendingRequests = requests.filter((request) => request.live_status === 'requested')
  const activeRequests = requests.filter((request) => request.live_status !== 'dropped')

  return (
    <div className="page-grid page-grid--stacked">
      <section className="panel">
        <div className="panel__header panel__header--split">
          <div>
            <p className="eyebrow">Operations flow</p>
            <h2>Dispatcher command board</h2>
            <p className="panel__lede">
              Monitor demand, trigger the pooling cycle, and rehearse the judge demo with a seeded morning rush.
            </p>
          </div>
          <div className="action-row">
            <button
              className="button button--secondary"
              type="button"
              disabled={busyAction !== null}
              onClick={() =>
                void runAction('dispatch', async () => {
                  const result = await api.runDispatch()
                  setBanner(
                    `Dispatched ${result.matched_requests} requests across ${result.routes_created} vans.`,
                  )
                })
              }
            >
              {busyAction === 'dispatch' ? 'Running...' : 'Run pooling cycle'}
            </button>
            <button
              className="button button--secondary"
              type="button"
              disabled={busyAction !== null}
              onClick={() =>
                void runAction('scenario', async () => {
                  const scenario = await api.loadMorningRush()
                  setBanner(`${scenario.created_requests} riders loaded for the morning rush demo.`)
                })
              }
            >
              {busyAction === 'scenario' ? 'Loading...' : 'Load morning rush'}
            </button>
            <button
              className="button button--ghost"
              type="button"
              disabled={busyAction !== null}
              onClick={() =>
                void runAction('reset', async () => {
                  const scenario = await api.resetDemo()
                  setBanner(scenario.details)
                })
              }
            >
              {busyAction === 'reset' ? 'Resetting...' : 'Reset demo'}
            </button>
          </div>
        </div>

        {banner ? <p className="notice notice--success">{banner}</p> : null}
        {error ? <p className="notice notice--error">{error}</p> : null}

        <div className="summary-grid summary-grid--four">
          <SummaryCard
            label="Active requests"
            value={`${summary?.active_requests ?? 0}`}
            helper={`${pendingRequests.length} waiting for the next cycle`}
          />
          <SummaryCard
            label="Matched riders"
            value={`${summary?.matched_requests ?? 0}`}
            helper="Riders already placed into pooled vans."
          />
          <SummaryCard
            label="Occupancy"
            value={formatPercentage(summary?.occupancy_rate ?? 0)}
            helper="How full the currently active vans are."
          />
          <SummaryCard
            label="Wait time saved"
            value={`${summary?.estimated_time_saved_minutes ?? 0} min`}
            helper="Vs. a fixed 18-minute baseline shuttle wait."
          />
        </div>
      </section>

      <MapView stops={allStops} routes={routes} vehicles={vehicles} title="Operations live map" />

      <section className="two-column-grid">
        <article className="panel">
          <div className="panel__header">
            <div>
              <p className="eyebrow">Requests</p>
              <h2>Demand queue</h2>
            </div>
          </div>

          <div className="list-stack">
            {activeRequests.length ? (
              activeRequests.map((request) => (
                <div className="list-card" key={request.id}>
                  <div className="list-card__header">
                    <div>
                      <h3>{request.rider_name}</h3>
                      <p>
                        {request.pickup_stop_name} to {request.destination_stop_name}
                      </p>
                    </div>
                    <StatusPill status={request.live_status} />
                  </div>
                  <div className="list-card__meta">
                    <span>{request.assigned_vehicle_name ?? 'Awaiting assignment'}</span>
                    <span>
                      ETA {request.pickup_eta_minutes ? `${request.pickup_eta_minutes} min` : 'TBD'}
                    </span>
                    <span>{request.passenger_count} seat(s)</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <h3>No commuter requests yet</h3>
                <p>Use the rider view or the seeded scenario to populate the dispatcher queue.</p>
              </div>
            )}
          </div>
        </article>

        <article className="panel">
          <div className="panel__header">
            <div>
              <p className="eyebrow">Fleet</p>
              <h2>Vehicle status</h2>
            </div>
          </div>

          <div className="list-stack">
            {vehicles.map((vehicle) => (
              <div className="list-card" key={vehicle.id}>
                <div className="list-card__header">
                  <div>
                    <h3>{vehicle.name}</h3>
                    <p>{vehicle.code}</p>
                  </div>
                  <StatusPill status={vehicle.status} />
                </div>
                <div className="list-card__meta">
                  <span>
                    Load {vehicle.occupancy}/{vehicle.seat_capacity}
                  </span>
                  <span>
                    Progress {Math.round(vehicle.progress_ratio * 100)}%
                  </span>
                  <span>{vehicle.assigned_route_id ? `Route ${vehicle.assigned_route_id}` : 'Idle at campus'}</span>
                </div>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="panel__header">
          <div>
            <p className="eyebrow">Routes</p>
            <h2>Active pooled routes</h2>
          </div>
        </div>

        <div className="route-grid">
          {routes.length ? (
            routes.map((route) => (
              <article className="route-card" key={route.id}>
                <div className="route-card__header">
                  <div>
                    <h3>{route.name}</h3>
                    <p>{route.summary}</p>
                  </div>
                  <StatusPill status={route.status} />
                </div>

                <div className="route-card__metrics">
                  <span>
                    {route.occupancy}/{route.capacity} riders
                  </span>
                  <span>{route.estimated_duration_minutes} min total</span>
                  <span>{Math.round(route.progress_ratio * 100)}% complete</span>
                </div>

                <ol className="stop-list">
                  {route.stops.map((stop) => (
                    <li key={`${route.id}-${stop.sequence}`}>
                      <strong>{stop.stop_name}</strong>
                      <span>
                        {stop.stop_type === 'pickup' ? '+' : ''}
                        {stop.passenger_delta} riders at {stop.eta_minutes} min
                      </span>
                    </li>
                  ))}
                </ol>
              </article>
            ))
          ) : (
            <div className="empty-state">
              <h3>No active routes yet</h3>
              <p>Run the pooling cycle or load the morning rush scenario to generate live routes.</p>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
