from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlmodel import Field, SQLModel


class StopKind(str, Enum):
    PICKUP = "pickup"
    DESTINATION = "destination"


class VehicleStatus(str, Enum):
    IDLE = "idle"
    ASSIGNED = "assigned"
    EN_ROUTE = "en_route"


class RequestStatus(str, Enum):
    REQUESTED = "requested"
    MATCHED = "matched"
    ARRIVING = "arriving"
    ONBOARD = "onboard"
    DROPPED = "dropped"


class RouteStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"


class CampusStop(SQLModel, table=True):
    __tablename__ = "stops"

    id: str = Field(primary_key=True)
    name: str
    code: str = Field(index=True, unique=True)
    kind: StopKind = Field(index=True)
    latitude: float
    longitude: float
    zone_group: str
    description: str | None = None


class Vehicle(SQLModel, table=True):
    __tablename__ = "vehicles"

    id: str = Field(primary_key=True)
    name: str
    code: str = Field(index=True, unique=True)
    seat_capacity: int
    status: VehicleStatus = Field(default=VehicleStatus.IDLE, index=True)
    home_stop_id: str | None = Field(default=None, foreign_key="stops.id")
    current_latitude: float
    current_longitude: float
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)


class RideRequest(SQLModel, table=True):
    __tablename__ = "requests"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    rider_name: str
    rider_team: str | None = None
    pickup_stop_id: str = Field(foreign_key="stops.id", index=True)
    destination_stop_id: str = Field(foreign_key="stops.id", index=True)
    desired_arrival_at: datetime
    passenger_count: int = Field(default=1, ge=1, le=4)
    status: RequestStatus = Field(default=RequestStatus.REQUESTED, index=True)
    assigned_vehicle_id: str | None = Field(default=None, foreign_key="vehicles.id")
    assigned_route_id: int | None = Field(default=None, foreign_key="routes.id")
    pickup_eta_minutes: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Route(SQLModel, table=True):
    __tablename__ = "routes"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    status: RouteStatus = Field(default=RouteStatus.PLANNED, index=True)
    vehicle_id: str = Field(foreign_key="vehicles.id", index=True)
    destination_stop_id: str = Field(foreign_key="stops.id", index=True)
    service_window: str = Field(default="morning-inbound")
    occupancy: int = 0
    estimated_duration_minutes: int = 0
    summary: str = ""
    geometry_json: str = "[]"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RouteStop(SQLModel, table=True):
    __tablename__ = "route_stops"

    id: int | None = Field(default=None, primary_key=True)
    route_id: int = Field(foreign_key="routes.id", index=True)
    stop_id: str = Field(foreign_key="stops.id", index=True)
    sequence: int
    stop_type: StopKind
    eta_minutes: int
    passenger_delta: int
    load_after_stop: int
    visited: bool = Field(default=False)
