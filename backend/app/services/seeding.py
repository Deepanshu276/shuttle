from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session, delete, select

from app.models import CampusStop, RideRequest, Route, RouteStop, StopKind, Vehicle, VehicleStatus

PICKUP_STOPS = [
    CampusStop(
        id="pickup-raidurg",
        name="Raidurg Metro Gate",
        code="RDM",
        kind=StopKind.PICKUP,
        latitude=17.4434,
        longitude=78.3783,
        zone_group="north_corridor",
        description="Metro-side pickup zone for early inbound commuters.",
    ),
    CampusStop(
        id="pickup-madhapur",
        name="Madhapur Bus Bay",
        code="MDB",
        kind=StopKind.PICKUP,
        latitude=17.4477,
        longitude=78.3908,
        zone_group="east_corridor",
        description="Shared stop for employees from the Madhapur corridor.",
    ),
    CampusStop(
        id="pickup-kondapur",
        name="Kondapur Junction",
        code="KDP",
        kind=StopKind.PICKUP,
        latitude=17.4698,
        longitude=78.3571,
        zone_group="northwest_corridor",
        description="Northern feeder stop with strong pooled demand.",
    ),
    CampusStop(
        id="pickup-gachibowli",
        name="Gachibowli Circle",
        code="GCB",
        kind=StopKind.PICKUP,
        latitude=17.4409,
        longitude=78.3487,
        zone_group="west_corridor",
        description="Pickup zone serving employees entering from the west.",
    ),
    CampusStop(
        id="pickup-financial-district",
        name="Financial District Hub",
        code="FDH",
        kind=StopKind.PICKUP,
        latitude=17.4253,
        longitude=78.3405,
        zone_group="southwest_corridor",
        description="High-demand stop for the southern business district.",
    ),
]

DESTINATION_STOPS = [
    CampusStop(
        id="dest-orion-west",
        name="Orion Tech Park West Gate",
        code="OTW",
        kind=StopKind.DESTINATION,
        latitude=17.4366,
        longitude=78.3678,
        zone_group="orion_campus",
        description="Primary inbound office destination for Tower A and B.",
    ),
    CampusStop(
        id="dest-orion-east",
        name="Orion Tech Park East Gate",
        code="OTE",
        kind=StopKind.DESTINATION,
        latitude=17.4381,
        longitude=78.3708,
        zone_group="orion_campus",
        description="Secondary destination for the east-side office blocks.",
    ),
]

REFERENCE_VEHICLES = [
    Vehicle(
        id="van-orbit-1",
        name="Orbit 1",
        code="ORB-1",
        seat_capacity=8,
        status=VehicleStatus.IDLE,
        home_stop_id="dest-orion-west",
        current_latitude=17.4362,
        current_longitude=78.3665,
    ),
    Vehicle(
        id="van-orbit-2",
        name="Orbit 2",
        code="ORB-2",
        seat_capacity=8,
        status=VehicleStatus.IDLE,
        home_stop_id="dest-orion-west",
        current_latitude=17.4371,
        current_longitude=78.3672,
    ),
    Vehicle(
        id="van-orbit-3",
        name="Orbit 3",
        code="ORB-3",
        seat_capacity=10,
        status=VehicleStatus.IDLE,
        home_stop_id="dest-orion-east",
        current_latitude=17.4386,
        current_longitude=78.3695,
    ),
]

VEHICLE_HOME_POSITIONS: dict[str, tuple[float, float]] = {
    "van-orbit-1": (17.4362, 78.3665),
    "van-orbit-2": (17.4371, 78.3672),
    "van-orbit-3": (17.4386, 78.3695),
}


def ensure_reference_data(session: Session) -> None:
    existing_stop_count = session.exec(select(CampusStop)).first()
    if existing_stop_count is None:
        for stop in [*PICKUP_STOPS, *DESTINATION_STOPS]:
            session.add(stop)

    existing_vehicle_count = session.exec(select(Vehicle)).first()
    if existing_vehicle_count is None:
        for vehicle in REFERENCE_VEHICLES:
            session.add(vehicle)

    session.commit()


def reset_demo_state(session: Session) -> None:
    session.exec(delete(RouteStop))
    session.exec(delete(Route))
    session.exec(delete(RideRequest))
    session.commit()

    vehicles = session.exec(select(Vehicle)).all()
    for vehicle in vehicles:
        home = VEHICLE_HOME_POSITIONS.get(vehicle.id)
        if home:
            vehicle.status = VehicleStatus.IDLE
            vehicle.current_latitude = home[0]
            vehicle.current_longitude = home[1]
            vehicle.last_updated_at = datetime.utcnow()
            session.add(vehicle)

    session.commit()


def load_morning_rush_scenario(session: Session) -> int:
    reset_demo_state(session)

    base_time = datetime.now().replace(second=0, microsecond=0)
    desired_base = base_time.replace(hour=9, minute=0)
    if desired_base <= base_time:
        desired_base = desired_base + timedelta(days=1)

    requests = [
        RideRequest(
            rider_name="Aisha",
            rider_team="Finance",
            pickup_stop_id="pickup-financial-district",
            destination_stop_id="dest-orion-west",
            desired_arrival_at=desired_base,
        ),
        RideRequest(
            rider_name="Rahul",
            rider_team="Security",
            pickup_stop_id="pickup-gachibowli",
            destination_stop_id="dest-orion-west",
            desired_arrival_at=desired_base,
        ),
        RideRequest(
            rider_name="Keerthi",
            rider_team="Design",
            pickup_stop_id="pickup-madhapur",
            destination_stop_id="dest-orion-east",
            desired_arrival_at=desired_base + timedelta(minutes=5),
        ),
        RideRequest(
            rider_name="Nikhil",
            rider_team="Engineering",
            pickup_stop_id="pickup-raidurg",
            destination_stop_id="dest-orion-east",
            desired_arrival_at=desired_base + timedelta(minutes=5),
        ),
        RideRequest(
            rider_name="Priya",
            rider_team="Engineering",
            pickup_stop_id="pickup-kondapur",
            destination_stop_id="dest-orion-west",
            desired_arrival_at=desired_base + timedelta(minutes=10),
        ),
        RideRequest(
            rider_name="Joseph",
            rider_team="HR",
            pickup_stop_id="pickup-madhapur",
            destination_stop_id="dest-orion-west",
            desired_arrival_at=desired_base + timedelta(minutes=10),
        ),
    ]

    for ride_request in requests:
        session.add(ride_request)

    session.commit()
    return len(requests)
