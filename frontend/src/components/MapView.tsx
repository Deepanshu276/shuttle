import { useEffect, useMemo, useRef } from 'react'
import L from 'leaflet'

import type { Route, Stop, Vehicle } from '../types'

interface MapViewProps {
  stops?: Stop[]
  routes?: Route[]
  vehicles?: Vehicle[]
  title?: string
}

export function MapView({
  stops = [],
  routes = [],
  vehicles = [],
  title = 'Live shuttle map',
}: MapViewProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<L.Map | null>(null)
  const layerGroupRef = useRef<L.LayerGroup | null>(null)

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

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) {
      return
    }

    const map = L.map(mapContainerRef.current, {
      zoomControl: true,
      scrollWheelZoom: true,
    }).setView([17.4366, 78.3678], 13)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map)

    mapRef.current = map
    layerGroupRef.current = L.layerGroup().addTo(map)

    return () => {
      map.remove()
      mapRef.current = null
      layerGroupRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    const layerGroup = layerGroupRef.current

    if (!map || !layerGroup) {
      return
    }

    layerGroup.clearLayers()

    for (const route of routes) {
      const polyline = L.polyline(
        route.geometry.map((point) => [point.latitude, point.longitude] as [number, number]),
        {
          color: route.id % 2 === 0 ? '#8b5cf6' : '#2563eb',
          weight: 5,
        },
      )
      polyline.bindPopup(`<strong>${route.name}</strong><br/>${route.summary}`)
      polyline.addTo(layerGroup)
    }

    for (const stop of stops) {
      const marker = L.circleMarker([stop.latitude, stop.longitude], {
        radius: stop.kind === 'pickup' ? 8 : 10,
        color: stop.kind === 'pickup' ? '#0f766e' : '#7c2d12',
        fillColor: stop.kind === 'pickup' ? '#14b8a6' : '#f97316',
        fillOpacity: 0.85,
      })

      marker.bindTooltip(stop.name, {
        direction: 'top',
        offset: [0, -10],
      })
      marker.addTo(layerGroup)
    }

    for (const vehicle of vehicles) {
      const marker = L.circleMarker([vehicle.current_latitude, vehicle.current_longitude], {
        radius: 11,
        color: '#111827',
        fillColor: '#111827',
        fillOpacity: 0.95,
      })
      marker.bindPopup(
        `<strong>${vehicle.name}</strong><br/>${vehicle.status.replace('_', ' ')} · ${vehicle.occupancy}/${vehicle.seat_capacity} seats`,
      )
      marker.addTo(layerGroup)
    }

    if (points.length === 0) {
      map.setView([17.4366, 78.3678], 13)
      return
    }

    if (points.length === 1) {
      map.setView(points[0], 13)
      return
    }

    map.fitBounds(L.latLngBounds(points), {
      padding: [32, 32],
    })
  }, [points, routes, stops, vehicles])

  return (
    <section className="map-card">
      <div className="map-card__header">
        <h3>{title}</h3>
        <p>Pickup zones, campus destinations, pooled routes, and van positions.</p>
      </div>
      <div className="map-canvas" ref={mapContainerRef} />
    </section>
  )
}
