import { useEffect, useMemo } from 'react'
import {
  CircleMarker,
  MapContainer,
  Polyline,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
} from 'react-leaflet'

import type { Route, Stop, Vehicle } from '../types'

interface MapViewProps {
  stops?: Stop[]
  routes?: Route[]
  vehicles?: Vehicle[]
  title?: string
}

function FitMap({
  points,
}: {
  points: Array<[number, number]>
}) {
  const map = useMap()

  useEffect(() => {
    if (points.length === 0) {
      return
    }

    if (points.length === 1) {
      map.setView(points[0], 13)
      return
    }

    map.fitBounds(points, { padding: [32, 32] })
  }, [map, points])

  return null
}

export function MapView({
  stops = [],
  routes = [],
  vehicles = [],
  title = 'Live shuttle map',
}: MapViewProps) {
  const routePoints = routes.flatMap((route) =>
    route.geometry.map((point) => [point.latitude, point.longitude] as [number, number]),
  )
  const stopPoints = stops.map((stop) => [stop.latitude, stop.longitude] as [number, number])
  const vehiclePoints = vehicles.map((vehicle) => [
    vehicle.current_latitude,
    vehicle.current_longitude,
  ] as [number, number])

  const points = useMemo(
    () => [...routePoints, ...stopPoints, ...vehiclePoints],
    [routePoints, stopPoints, vehiclePoints],
  )

  const center = points[0] ?? ([17.4366, 78.3678] as [number, number])

  return (
    <section className="map-card">
      <div className="map-card__header">
        <h3>{title}</h3>
        <p>Pickup zones, campus destinations, pooled routes, and van positions.</p>
      </div>
      <MapContainer center={center} zoom={13} scrollWheelZoom className="map-canvas">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitMap points={points} />

        {routes.map((route) => (
          <Polyline
            key={route.id}
            positions={route.geometry.map((point) => [point.latitude, point.longitude])}
            pathOptions={{ color: route.id % 2 === 0 ? '#8b5cf6' : '#2563eb', weight: 5 }}
          >
            <Popup>
              <strong>{route.name}</strong>
              <br />
              {route.summary}
            </Popup>
          </Polyline>
        ))}

        {stops.map((stop) => (
          <CircleMarker
            key={stop.id}
            center={[stop.latitude, stop.longitude]}
            radius={stop.kind === 'pickup' ? 8 : 10}
            pathOptions={{
              color: stop.kind === 'pickup' ? '#0f766e' : '#7c2d12',
              fillColor: stop.kind === 'pickup' ? '#14b8a6' : '#f97316',
              fillOpacity: 0.85,
            }}
          >
            <Tooltip direction="top" offset={[0, -10]}>
              {stop.name}
            </Tooltip>
          </CircleMarker>
        ))}

        {vehicles.map((vehicle) => (
          <CircleMarker
            key={vehicle.id}
            center={[vehicle.current_latitude, vehicle.current_longitude]}
            radius={11}
            pathOptions={{ color: '#111827', fillColor: '#111827', fillOpacity: 0.95 }}
          >
            <Popup>
              <strong>{vehicle.name}</strong>
              <br />
              {vehicle.status.replace('_', ' ')} · {vehicle.occupancy}/{vehicle.seat_capacity} seats
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </section>
  )
}
