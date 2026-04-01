# Corporate Shuttle

A demand-responsive shuttle system for corporate campuses and business parks. Employees request pooled rides on-demand, the backend batches requests and dynamically routes vans based on real-time demand, and the operations dashboard visualizes live routes, occupancy, and ETA updates.

## Problem

Office shuttles typically run on fixed routes and fixed schedules — vans stop at every zone regardless of whether anyone is waiting. This wastes time and capacity.

This system routes vans based on actual demand: stops with more waiting passengers are visited first, empty stops are skipped, and routes update as new requests arrive.

## How It Works

1. Employees book rides by selecting a pickup zone and desired arrival time.
2. The dispatch engine groups requests by destination and time window, assigns the closest available van, and orders pickup stops using a demand-weighted heuristic — `score = distance / passengers_waiting`.
3. Ops dispatchers can re-optimize any active route mid-trip, reordering remaining stops based on requests that have come in since the route was built.

## Stack

- Backend: `FastAPI` + `SQLModel` + `SQLite`
- Frontend: `React` + `Vite` + `React Router`
- Maps: `Leaflet` + `OpenStreetMap`

## Project Structure

```text
backend/
  app/
    main.py
    models.py
    schemas.py
    services/
      dispatch.py
      seeding.py
frontend/
  src/
    components/
    pages/
docs/
  demo-script.md
```

## Running Locally

**Backend**

```bash
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

API available at `http://127.0.0.1:8000`, routes mounted under `/api`.

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Vite dev server proxies `/api` to the FastAPI backend.

## Usage

1. Open `/rider` to book a ride — select a pickup zone, destination, and arrival time.
2. Open `/ops` to see the dispatcher dashboard — run the pooling cycle to assign vans.
3. Click **Re-optimize** on any active route to reorder remaining stops based on current demand.
4. Use **Load morning rush** to seed a sample scenario and auto-dispatch.
5. Use **Reset** to clear all rides and return vans to home positions.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/stops` | Pickup zones and destinations |
| `POST` | `/api/requests` | Submit a ride request |
| `GET` | `/api/requests` | All ride requests |
| `GET` | `/api/routes` | Active routes with stops and geometry |
| `GET` | `/api/vehicles` | Van status and positions |
| `GET` | `/api/dashboard/summary` | Occupancy, wait time, and pooling metrics |
| `POST` | `/api/dispatch/run` | Run the pooling and routing cycle |
| `POST` | `/api/routes/{id}/reoptimize` | Re-optimize stop order based on live demand |
| `POST` | `/api/demo/reset` | Clear all rides, reset vans to home |
| `POST` | `/api/demo/scenario/morning-rush` | Load a sample scenario and dispatch |
