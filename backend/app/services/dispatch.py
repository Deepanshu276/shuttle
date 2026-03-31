from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime

from sqlmodel import Session, delete, select

from app.models import (
    CampusStop,
    RequestStatus,
    RideRequest,
    Route,
    RouteStatus,
    RouteStop,
    StopKind,
    Vehicle,
    VehicleStatus,
)
from app.schemas import (
    Coordinate,
    DashboardSummary,
    DispatchRunResult,
    RideRequestRead,
    RouteRead,
    RouteStopRead,
    VehicleRead,
)

AVERAGE_SPEED_KMPH = 22
BASELINE_FIXED_WAIT_MINUTES = 18


def haversine_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    radius_km = 6371
    lat_a = math.radians(latitude_a)
    lat_b = math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lng = math.radians(longitude_b - longitude_a)

    arc = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lng / 2) ** 2
    )
    return radius_km * (2 * math.atan2(math.sqrt(arc), math.sqrt(1 - arc)))


def estimate_drive_minutes(distance_km: float) -> int:
    minutes = max(3, round((distance_km / AVERAGE_SPEED_KMPH) * 60))
    return minutes


def bucketize_arrival_window(desired_arrival_at: datetime) -> datetime:
    bucket_minute = (desired_arrival_at.minute // 15) * 15
    return desired_arrival_at.replace(minute=bucket_minute, second=0, microsecond=0)


def route_progress_ratio(route: Route) -> float:
    if route.estimated_duration_minutes <= 0:
        return 0.0

    elapsed_minutes = (datetime.utcnow() - route.started_at).total_seconds() / 60
    return max(0.0, min(1.0, elapsed_minutes / route.estimated_duration_minutes))


def route_status(route: Route) -> RouteStatus:
    return RouteStatus.COMPLETED if route_progress_ratio(route) >= 1 else RouteStatus.ACTIVE


def parse_geometry(route: Route) -> list[Coordinate]:
    raw_geometry = json.loads(route.geometry_json)
    return [Coordinate(**point) for point in raw_geometry]


def interpolate_coordinate(geometry: list[Coordinate], progress_ratio: float) -> Coordinate:
    if not geometry:
        return Coordinate(latitude=0.0, longitude=0.0)
    if len(geometry) == 1:
        return geometry[0]

    clamped_ratio = max(0.0, min(1.0, progress_ratio))
    if clamped_ratio == 0:
        return geometry[0]
    if clamped_ratio == 1:
        return geometry[-1]

    segment_lengths: list[float] = []
    total_length = 0.0
    for index in range(len(geometry) - 1):
        segment_length = haversine_km(
            geometry[index].latitude,
            geometry[index].longitude,
            geometry[index + 1].latitude,
            geometry[index + 1].longitude,
        )
        segment_lengths.append(segment_length)
        total_length += segment_length

    if total_length == 0:
        return geometry[0]

    target_distance = total_length * clamped_ratio
    traversed = 0.0
    for index, segment_length in enumerate(segment_lengths):
        if traversed + segment_length >= target_distance:
            segment_ratio = (target_distance - traversed) / segment_length if segment_length else 0
            start = geometry[index]
            end = geometry[index + 1]
            latitude = start.latitude + (end.latitude - start.latitude) * segment_ratio
            longitude = start.longitude + (end.longitude - start.longitude) * segment_ratio
            return Coordinate(latitude=latitude, longitude=longitude)
        traversed += segment_length

    return geometry[-1]


def request_live_status(ride_request: RideRequest, route: Route | None) -> RequestStatus:
    if ride_request.status == RequestStatus.DROPPED:
        return RequestStatus.DROPPED
    if route is None or ride_request.assigned_route_id is None:
        return RequestStatus.REQUESTED

    elapsed_minutes = (datetime.utcnow() - route.started_at).total_seconds() / 60
    pickup_eta = ride_request.pickup_eta_minutes or 0
    destination_eta = route.estimated_duration_minutes

    if elapsed_minutes < max(pickup_eta - 2, 0):
        return RequestStatus.MATCHED
    if elapsed_minutes < pickup_eta + 1:
        return RequestStatus.ARRIVING
    if elapsed_minutes < destination_eta:
        return RequestStatus.ONBOARD
    return RequestStatus.DROPPED


def nearest_neighbor_order(
    pickup_ids: list[str],
    stops_by_id: dict[str, CampusStop],
    start_latitude: float,
    start_longitude: float,
) -> list[str]:
    remaining = pickup_ids[:]
    ordered: list[str] = []
    current_latitude = start_latitude
    current_longitude = start_longitude

    while remaining:
        next_stop_id = min(
            remaining,
            key=lambda stop_id: haversine_km(
                current_latitude,
                current_longitude,
                stops_by_id[stop_id].latitude,
                stops_by_id[stop_id].longitude,
            ),
        )
        ordered.append(next_stop_id)
        current_latitude = stops_by_id[next_stop_id].latitude
        current_longitude = stops_by_id[next_stop_id].longitude
        remaining.remove(next_stop_id)

    return ordered


def split_requests_for_vehicle(
    ride_requests: list[RideRequest],
    seat_capacity: int,
) -> tuple[list[RideRequest], list[RideRequest]]:
    assigned: list[RideRequest] = []
    overflow: list[RideRequest] = []
    used_seats = 0

    for ride_request in ride_requests:
        if used_seats + ride_request.passenger_count <= seat_capacity:
            assigned.append(ride_request)
            used_seats += ride_request.passenger_count
        else:
            overflow.append(ride_request)

    return assigned, overflow


def choose_vehicle(
    available_vehicles: list[Vehicle],
    ride_requests: list[RideRequest],
    stops_by_id: dict[str, CampusStop],
) -> Vehicle:
    pickup_stops = [stops_by_id[ride_request.pickup_stop_id] for ride_request in ride_requests]
    centroid_latitude = sum(stop.latitude for stop in pickup_stops) / len(pickup_stops)
    centroid_longitude = sum(stop.longitude for stop in pickup_stops) / len(pickup_stops)

    return min(
        available_vehicles,
        key=lambda vehicle: haversine_km(
            vehicle.current_latitude,
            vehicle.current_longitude,
            centroid_latitude,
            centroid_longitude,
        ),
    )


def sync_completed_requests(session: Session) -> None:
    routes = session.exec(select(Route)).all()
    if not routes:
        return

    routes_by_id = {route.id: route for route in routes if route.id is not None}
    ride_requests = session.exec(select(RideRequest)).all()
    changed = False

    for ride_request in ride_requests:
        if ride_request.assigned_route_id is None:
            continue

        route = routes_by_id.get(ride_request.assigned_route_id)
        if route is None:
            continue

        live_status = request_live_status(ride_request, route)
        if live_status == RequestStatus.DROPPED and ride_request.status != RequestStatus.DROPPED:
            ride_request.status = RequestStatus.DROPPED
            session.add(ride_request)
            changed = True

    if changed:
        session.commit()


def run_dispatch(session: Session) -> DispatchRunResult:
    sync_completed_requests(session)

    stops = session.exec(select(CampusStop)).all()
    stops_by_id = {stop.id: stop for stop in stops}

    ride_requests = session.exec(
        select(RideRequest).where(RideRequest.status != RequestStatus.DROPPED).order_by(
            RideRequest.desired_arrival_at,
            RideRequest.created_at,
        )
    ).all()
    vehicles = session.exec(select(Vehicle).order_by(Vehicle.code)).all()

    for ride_request in ride_requests:
        ride_request.assigned_vehicle_id = None
        ride_request.assigned_route_id = None
        ride_request.pickup_eta_minutes = None
        ride_request.status = RequestStatus.REQUESTED
        session.add(ride_request)

    session.exec(delete(RouteStop))
    session.exec(delete(Route))

    for vehicle in vehicles:
        vehicle.status = VehicleStatus.IDLE
        vehicle.last_updated_at = datetime.utcnow()
        session.add(vehicle)

    session.commit()

    if not ride_requests:
        return DispatchRunResult(routes_created=0, matched_requests=0, pending_requests=0)

    grouped_requests: dict[tuple[str, datetime], list[RideRequest]] = defaultdict(list)
    for ride_request in ride_requests:
        grouped_requests[
            (ride_request.destination_stop_id, bucketize_arrival_window(ride_request.desired_arrival_at))
        ].append(ride_request)

    available_vehicles = vehicles[:]
    matched_requests = 0
    routes_created = 0

    for _, grouped in sorted(grouped_requests.items(), key=lambda item: (item[0][1], item[0][0])):
        remaining = sorted(grouped, key=lambda request_item: request_item.created_at)

        while remaining and available_vehicles:
            vehicle = choose_vehicle(available_vehicles, remaining, stops_by_id)
            assigned_chunk, remaining = split_requests_for_vehicle(remaining, vehicle.seat_capacity)
            if not assigned_chunk:
                break

            route = build_route(session, vehicle, assigned_chunk, stops_by_id)
            routes_created += 1
            matched_requests += len(assigned_chunk)
            available_vehicles = [candidate for candidate in available_vehicles if candidate.id != vehicle.id]

            if route.id is None:
                raise RuntimeError("Route was not persisted correctly.")

    session.commit()
    pending_requests = len(ride_requests) - matched_requests
    return DispatchRunResult(
        routes_created=routes_created,
        matched_requests=matched_requests,
        pending_requests=pending_requests,
    )


def build_route(
    session: Session,
    vehicle: Vehicle,
    assigned_requests: list[RideRequest],
    stops_by_id: dict[str, CampusStop],
) -> Route:
    destination_stop = stops_by_id[assigned_requests[0].destination_stop_id]
    pickup_loads: dict[str, int] = defaultdict(int)
    total_passengers = 0

    for ride_request in assigned_requests:
        pickup_loads[ride_request.pickup_stop_id] += ride_request.passenger_count
        total_passengers += ride_request.passenger_count

    ordered_pickups = nearest_neighbor_order(
        list(pickup_loads.keys()),
        stops_by_id,
        vehicle.current_latitude,
        vehicle.current_longitude,
    )

    route = Route(
        name=f"{vehicle.name} to {destination_stop.code}",
        status=RouteStatus.ACTIVE,
        vehicle_id=vehicle.id,
        destination_stop_id=destination_stop.id,
        occupancy=total_passengers,
        summary=(
            f"{len(ordered_pickups)} pickup zones, {total_passengers} riders, "
            f"destination {destination_stop.name}"
        ),
        started_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(route)
    session.flush()

    geometry = [
        {
            "latitude": vehicle.current_latitude,
            "longitude": vehicle.current_longitude,
        }
    ]

    current_latitude = vehicle.current_latitude
    current_longitude = vehicle.current_longitude
    elapsed_minutes = 0
    onboard_load = 0
    sequence = 1

    for pickup_id in ordered_pickups:
        pickup_stop = stops_by_id[pickup_id]
        travel_minutes = estimate_drive_minutes(
            haversine_km(
                current_latitude,
                current_longitude,
                pickup_stop.latitude,
                pickup_stop.longitude,
            )
        )
        elapsed_minutes += travel_minutes
        onboard_load += pickup_loads[pickup_id]

        session.add(
            RouteStop(
                route_id=route.id,
                stop_id=pickup_stop.id,
                sequence=sequence,
                stop_type=StopKind.PICKUP,
                eta_minutes=elapsed_minutes,
                passenger_delta=pickup_loads[pickup_id],
                load_after_stop=onboard_load,
            )
        )
        geometry.append({"latitude": pickup_stop.latitude, "longitude": pickup_stop.longitude})

        for ride_request in assigned_requests:
            if ride_request.pickup_stop_id == pickup_id:
                ride_request.assigned_vehicle_id = vehicle.id
                ride_request.assigned_route_id = route.id
                ride_request.pickup_eta_minutes = elapsed_minutes
                ride_request.status = RequestStatus.MATCHED
                session.add(ride_request)

        current_latitude = pickup_stop.latitude
        current_longitude = pickup_stop.longitude
        sequence += 1

    destination_minutes = estimate_drive_minutes(
        haversine_km(
            current_latitude,
            current_longitude,
            destination_stop.latitude,
            destination_stop.longitude,
        )
    )
    elapsed_minutes += destination_minutes

    session.add(
        RouteStop(
            route_id=route.id,
            stop_id=destination_stop.id,
            sequence=sequence,
            stop_type=StopKind.DESTINATION,
            eta_minutes=elapsed_minutes,
            passenger_delta=-total_passengers,
            load_after_stop=0,
        )
    )

    geometry.append(
        {"latitude": destination_stop.latitude, "longitude": destination_stop.longitude}
    )
    route.geometry_json = json.dumps(geometry)
    route.estimated_duration_minutes = elapsed_minutes + 2
    route.updated_at = datetime.utcnow()

    vehicle.status = VehicleStatus.ASSIGNED
    vehicle.last_updated_at = datetime.utcnow()
    session.add(vehicle)
    session.add(route)
    session.flush()
    return route


def list_requests(session: Session) -> list[RideRequestRead]:
    stops = session.exec(select(CampusStop)).all()
    stops_by_id = {stop.id: stop for stop in stops}
    vehicles = session.exec(select(Vehicle)).all()
    vehicles_by_id = {vehicle.id: vehicle for vehicle in vehicles}
    routes = session.exec(select(Route)).all()
    routes_by_id = {route.id: route for route in routes if route.id is not None}
    ride_requests = session.exec(
        select(RideRequest).order_by(RideRequest.created_at.desc())
    ).all()

    serialized: list[RideRequestRead] = []
    for ride_request in ride_requests:
        route = routes_by_id.get(ride_request.assigned_route_id)
        vehicle = vehicles_by_id.get(ride_request.assigned_vehicle_id)
        live_status = request_live_status(ride_request, route)
        destination_eta = route.estimated_duration_minutes if route else None
        serialized.append(
            RideRequestRead(
                id=ride_request.id,
                rider_name=ride_request.rider_name,
                rider_team=ride_request.rider_team,
                pickup_stop_id=ride_request.pickup_stop_id,
                pickup_stop_name=stops_by_id[ride_request.pickup_stop_id].name,
                destination_stop_id=ride_request.destination_stop_id,
                destination_stop_name=stops_by_id[ride_request.destination_stop_id].name,
                desired_arrival_at=ride_request.desired_arrival_at,
                passenger_count=ride_request.passenger_count,
                status=ride_request.status,
                live_status=live_status,
                assigned_vehicle_id=ride_request.assigned_vehicle_id,
                assigned_vehicle_name=vehicle.name if vehicle else None,
                assigned_route_id=ride_request.assigned_route_id,
                pickup_eta_minutes=ride_request.pickup_eta_minutes,
                destination_eta_minutes=destination_eta,
                route_progress=route_progress_ratio(route) if route else 0.0,
                created_at=ride_request.created_at,
            )
        )

    return serialized


def get_request_detail(session: Session, request_id: str) -> RideRequestRead | None:
    return next(
        (ride_request for ride_request in list_requests(session) if ride_request.id == request_id),
        None,
    )


def list_routes(session: Session) -> list[RouteRead]:
    stops = session.exec(select(CampusStop)).all()
    stops_by_id = {stop.id: stop for stop in stops}
    vehicles = session.exec(select(Vehicle)).all()
    vehicles_by_id = {vehicle.id: vehicle for vehicle in vehicles}
    routes = session.exec(select(Route).order_by(Route.started_at)).all()

    serialized: list[RouteRead] = []
    for route in routes:
        if route.id is None:
            continue

        vehicle = vehicles_by_id[route.vehicle_id]
        route_stops = session.exec(
            select(RouteStop).where(RouteStop.route_id == route.id).order_by(RouteStop.sequence)
        ).all()
        geometry = parse_geometry(route)
        serialized_stops = [
            RouteStopRead(
                sequence=route_stop.sequence,
                stop_id=route_stop.stop_id,
                stop_name=stops_by_id[route_stop.stop_id].name,
                stop_type=route_stop.stop_type,
                latitude=stops_by_id[route_stop.stop_id].latitude,
                longitude=stops_by_id[route_stop.stop_id].longitude,
                eta_minutes=route_stop.eta_minutes,
                passenger_delta=route_stop.passenger_delta,
                load_after_stop=route_stop.load_after_stop,
            )
            for route_stop in route_stops
        ]

        serialized.append(
            RouteRead(
                id=route.id,
                name=route.name,
                status=route_status(route),
                vehicle_id=route.vehicle_id,
                vehicle_name=vehicle.name,
                destination_stop_id=route.destination_stop_id,
                destination_stop_name=stops_by_id[route.destination_stop_id].name,
                occupancy=route.occupancy,
                capacity=vehicle.seat_capacity,
                estimated_duration_minutes=route.estimated_duration_minutes,
                summary=route.summary,
                started_at=route.started_at,
                progress_ratio=route_progress_ratio(route),
                geometry=geometry,
                stops=serialized_stops,
            )
        )

    return serialized


def list_vehicles(session: Session) -> list[VehicleRead]:
    routes = session.exec(select(Route)).all()
    active_routes_by_vehicle = {route.vehicle_id: route for route in routes if route_status(route) != RouteStatus.COMPLETED}
    vehicles = session.exec(select(Vehicle).order_by(Vehicle.code)).all()

    serialized: list[VehicleRead] = []
    for vehicle in vehicles:
        active_route = active_routes_by_vehicle.get(vehicle.id)
        geometry = parse_geometry(active_route) if active_route else []
        progress = route_progress_ratio(active_route) if active_route else 0.0
        display_coordinate = (
            interpolate_coordinate(geometry, progress) if active_route else Coordinate(
                latitude=vehicle.current_latitude,
                longitude=vehicle.current_longitude,
            )
        )

        status = vehicle.status
        if active_route:
            status = VehicleStatus.EN_ROUTE if progress > 0 else VehicleStatus.ASSIGNED
        else:
            status = VehicleStatus.IDLE

        serialized.append(
            VehicleRead(
                id=vehicle.id,
                name=vehicle.name,
                code=vehicle.code,
                seat_capacity=vehicle.seat_capacity,
                status=status,
                occupancy=active_route.occupancy if active_route else 0,
                assigned_route_id=active_route.id if active_route else None,
                progress_ratio=progress,
                current_latitude=display_coordinate.latitude,
                current_longitude=display_coordinate.longitude,
            )
        )

    return serialized


def dashboard_summary(session: Session) -> DashboardSummary:
    requests = list_requests(session)
    routes = list_routes(session)
    active_routes = [route for route in routes if route.status != RouteStatus.COMPLETED]
    matched_requests = [
        request
        for request in requests
        if request.live_status in {RequestStatus.MATCHED, RequestStatus.ARRIVING, RequestStatus.ONBOARD}
    ]
    pooled_rides = sum(route.occupancy for route in active_routes if route.occupancy > 1)
    average_wait = round(
        sum(request.pickup_eta_minutes or 0 for request in matched_requests) / len(matched_requests)
    ) if matched_requests else 0
    total_capacity = sum(route.capacity for route in active_routes)
    occupancy_rate = (
        round(sum(route.occupancy for route in active_routes) / total_capacity, 2) if total_capacity else 0.0
    )
    estimated_time_saved = max(0, BASELINE_FIXED_WAIT_MINUTES - average_wait) * len(matched_requests)

    return DashboardSummary(
        active_requests=len([request for request in requests if request.live_status != RequestStatus.DROPPED]),
        matched_requests=len(matched_requests),
        pooled_rides=pooled_rides,
        active_vehicles=len(active_routes),
        average_wait_minutes=average_wait,
        occupancy_rate=occupancy_rate,
        estimated_time_saved_minutes=estimated_time_saved,
    )
