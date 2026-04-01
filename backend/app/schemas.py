from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models import RequestStatus, RouteStatus, StopKind, VehicleStatus


class Coordinate(BaseModel):
    latitude: float
    longitude: float


class StopRead(BaseModel):
    id: str
    name: str
    code: str
    kind: StopKind
    latitude: float
    longitude: float
    zone_group: str
    description: str | None = None


class StopsCatalog(BaseModel):
    pickups: list[StopRead]
    destinations: list[StopRead]


class RideRequestCreate(BaseModel):
    rider_name: str = Field(min_length=2, max_length=60)
    rider_team: str | None = Field(default=None, max_length=60)
    pickup_stop_id: str
    destination_stop_id: str
    desired_arrival_at: datetime
    passenger_count: int = Field(default=1, ge=1, le=4)


class RideRequestRead(BaseModel):
    id: str
    rider_name: str
    rider_team: str | None = None
    pickup_stop_id: str
    pickup_stop_name: str
    destination_stop_id: str
    destination_stop_name: str
    desired_arrival_at: datetime
    passenger_count: int
    status: RequestStatus
    live_status: RequestStatus
    assigned_vehicle_id: str | None = None
    assigned_vehicle_name: str | None = None
    assigned_route_id: int | None = None
    pickup_eta_minutes: int | None = None
    destination_eta_minutes: int | None = None
    route_progress: float = 0.0
    created_at: datetime


class RouteStopRead(BaseModel):
    sequence: int
    stop_id: str
    stop_name: str
    stop_type: StopKind
    latitude: float
    longitude: float
    eta_minutes: int
    passenger_delta: int
    load_after_stop: int
    visited: bool


class RouteRead(BaseModel):
    id: int
    name: str
    status: RouteStatus
    vehicle_id: str
    vehicle_name: str
    destination_stop_id: str
    destination_stop_name: str
    occupancy: int
    capacity: int
    estimated_duration_minutes: int
    summary: str
    started_at: datetime
    progress_ratio: float
    geometry: list[Coordinate]
    stops: list[RouteStopRead]


class VehicleRead(BaseModel):
    id: str
    name: str
    code: str
    seat_capacity: int
    status: VehicleStatus
    occupancy: int
    assigned_route_id: int | None = None
    progress_ratio: float = 0.0
    current_latitude: float
    current_longitude: float


class DashboardSummary(BaseModel):
    active_requests: int
    matched_requests: int
    pooled_rides: int
    active_vehicles: int
    average_wait_minutes: int
    occupancy_rate: float
    estimated_time_saved_minutes: int


class DispatchRunResult(BaseModel):
    routes_created: int
    matched_requests: int
    pending_requests: int


class DemoScenarioRead(BaseModel):
    scenario_name: str
    created_requests: int
    details: str
