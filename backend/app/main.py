from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, select

from app.database import engine, get_session
from app.models import CampusStop, RideRequest, StopKind
from app.schemas import (
    DashboardSummary,
    DemoScenarioRead,
    DispatchRunResult,
    RideRequestCreate,
    RideRequestRead,
    RouteRead,
    StopRead,
    StopsCatalog,
    VehicleRead,
)
from app.services.dispatch import (
    dashboard_summary,
    get_request_detail,
    list_requests,
    list_routes,
    list_vehicles,
    reoptimize_route,
    run_dispatch,
    sync_completed_requests,
)
from app.services.seeding import ensure_reference_data, load_morning_rush_scenario, reset_demo_state


@asynccontextmanager
async def lifespan(_: FastAPI):
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        ensure_reference_data(session)
    yield


app = FastAPI(
    title="Corporate Shuttle API",
    description="Demand-responsive shuttle pooling backend for a hackathon MVP.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


@api.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@api.get("/stops", response_model=StopsCatalog)
def get_stops(session: Session = Depends(get_session)) -> StopsCatalog:
    stops = session.exec(select(CampusStop).order_by(CampusStop.name)).all()
    pickups = [StopRead.model_validate(stop, from_attributes=True) for stop in stops if stop.kind == StopKind.PICKUP]
    destinations = [
        StopRead.model_validate(stop, from_attributes=True) for stop in stops if stop.kind == StopKind.DESTINATION
    ]
    return StopsCatalog(pickups=pickups, destinations=destinations)


@api.post("/requests", response_model=RideRequestRead, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: RideRequestCreate,
    session: Session = Depends(get_session),
) -> RideRequestRead:
    pickup_stop = session.get(CampusStop, payload.pickup_stop_id)
    destination_stop = session.get(CampusStop, payload.destination_stop_id)

    if pickup_stop is None or pickup_stop.kind != StopKind.PICKUP:
        raise HTTPException(status_code=404, detail="Pickup zone not found.")
    if destination_stop is None or destination_stop.kind != StopKind.DESTINATION:
        raise HTTPException(status_code=404, detail="Destination stop not found.")
    if pickup_stop.id == destination_stop.id:
        raise HTTPException(status_code=400, detail="Pickup and destination cannot match.")

    ride_request = RideRequest(**payload.model_dump())
    session.add(ride_request)
    session.commit()
    session.refresh(ride_request)

    request_detail = get_request_detail(session, ride_request.id)
    if request_detail is None:
        raise HTTPException(status_code=500, detail="Request could not be created.")
    return request_detail


@api.get("/requests", response_model=list[RideRequestRead])
def get_requests(session: Session = Depends(get_session)) -> list[RideRequestRead]:
    sync_completed_requests(session)
    return list_requests(session)


@api.get("/requests/{request_id}", response_model=RideRequestRead)
def get_request(
    request_id: str,
    session: Session = Depends(get_session),
) -> RideRequestRead:
    sync_completed_requests(session)
    ride_request = get_request_detail(session, request_id)
    if ride_request is None:
        raise HTTPException(status_code=404, detail="Request not found.")
    return ride_request


@api.get("/routes", response_model=list[RouteRead])
def get_routes(session: Session = Depends(get_session)) -> list[RouteRead]:
    sync_completed_requests(session)
    return list_routes(session)


@api.post("/routes/{route_id}/reoptimize", response_model=RouteRead)
def trigger_reoptimize(
    route_id: int,
    session: Session = Depends(get_session),
) -> RouteRead:
    try:
        return reoptimize_route(route_id, session)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@api.get("/vehicles", response_model=list[VehicleRead])
def get_vehicles(session: Session = Depends(get_session)) -> list[VehicleRead]:
    sync_completed_requests(session)
    return list_vehicles(session)


@api.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(session: Session = Depends(get_session)) -> DashboardSummary:
    sync_completed_requests(session)
    return dashboard_summary(session)


@api.post("/dispatch/run", response_model=DispatchRunResult)
def trigger_dispatch(session: Session = Depends(get_session)) -> DispatchRunResult:
    ensure_reference_data(session)
    return run_dispatch(session)


@api.post("/demo/reset", response_model=DemoScenarioRead)
def reset_demo(session: Session = Depends(get_session)) -> DemoScenarioRead:
    ensure_reference_data(session)
    reset_demo_state(session)
    return DemoScenarioRead(
        scenario_name="clean-slate",
        created_requests=0,
        details="Reset to the seeded campus with three idle vans and no active commuter requests.",
    )


@api.post("/demo/scenario/morning-rush", response_model=DemoScenarioRead)
def load_morning_rush(session: Session = Depends(get_session)) -> DemoScenarioRead:
    ensure_reference_data(session)
    created_requests = load_morning_rush_scenario(session)
    run_dispatch(session)
    return DemoScenarioRead(
        scenario_name="morning-rush",
        created_requests=created_requests,
        details="Loaded a six-rider morning inbound rush and dispatched pooled vans automatically.",
    )


app.include_router(api)
