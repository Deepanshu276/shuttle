export type StopKind = 'pickup' | 'destination'
export type RequestStatus = 'requested' | 'matched' | 'arriving' | 'onboard' | 'dropped'
export type RouteStatus = 'planned' | 'active' | 'completed'
export type VehicleStatus = 'idle' | 'assigned' | 'en_route'

export interface Stop {
  id: string
  name: string
  code: string
  kind: StopKind
  latitude: number
  longitude: number
  zone_group: string
  description?: string | null
}

export interface StopsCatalog {
  pickups: Stop[]
  destinations: Stop[]
}

export interface RideRequestPayload {
  rider_name: string
  rider_team?: string
  pickup_stop_id: string
  destination_stop_id: string
  desired_arrival_at: string
  passenger_count: number
}

export interface RideRequest {
  id: string
  rider_name: string
  rider_team?: string | null
  pickup_stop_id: string
  pickup_stop_name: string
  destination_stop_id: string
  destination_stop_name: string
  desired_arrival_at: string
  passenger_count: number
  status: RequestStatus
  live_status: RequestStatus
  assigned_vehicle_id?: string | null
  assigned_vehicle_name?: string | null
  assigned_route_id?: number | null
  pickup_eta_minutes?: number | null
  destination_eta_minutes?: number | null
  route_progress: number
  created_at: string
}

export interface Coordinate {
  latitude: number
  longitude: number
}

export interface RouteStop {
  sequence: number
  stop_id: string
  stop_name: string
  stop_type: StopKind
  latitude: number
  longitude: number
  eta_minutes: number
  passenger_delta: number
  load_after_stop: number
}

export interface Route {
  id: number
  name: string
  status: RouteStatus
  vehicle_id: string
  vehicle_name: string
  destination_stop_id: string
  destination_stop_name: string
  occupancy: number
  capacity: number
  estimated_duration_minutes: number
  summary: string
  started_at: string
  progress_ratio: number
  geometry: Coordinate[]
  stops: RouteStop[]
}

export interface Vehicle {
  id: string
  name: string
  code: string
  seat_capacity: number
  status: VehicleStatus
  occupancy: number
  assigned_route_id?: number | null
  progress_ratio: number
  current_latitude: number
  current_longitude: number
}

export interface DashboardSummary {
  active_requests: number
  matched_requests: number
  pooled_rides: number
  active_vehicles: number
  average_wait_minutes: number
  occupancy_rate: number
  estimated_time_saved_minutes: number
}

export interface DispatchRunResult {
  routes_created: number
  matched_requests: number
  pending_requests: number
}

export interface DemoScenario {
  scenario_name: string
  created_requests: number
  details: string
}
