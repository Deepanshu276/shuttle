# Corporate Shuttle MVP

Demand-responsive corporate shuttle prototype for a hackathon. Employees request pooled rides to a business park, the backend batches and assigns riders to vans, and the operations dashboard visualizes live routes, occupancy, and ETA updates.

## Stack

- Backend: `FastAPI` + `SQLModel` + `SQLite`
- Frontend: `React` + `Vite` + `React Router`
- Maps: `Leaflet` + `OpenStreetMap`

## MVP Scope

- One business park: `Orion Tech Park`
- One service window: `morning inbound`
- Three vans with fixed seat capacities
- Five pickup zones and two campus destinations
- Demand-responsive batching with a lightweight dispatch heuristic

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

## Run The Backend

```bash
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`, with routes mounted under `/api`.

## Run The Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to the FastAPI backend.

## Demo Workflow

1. Open the rider view at `/rider` and create one or two manual ride requests.
2. Open the operations view at `/ops` and run the pooling cycle.
3. For a faster scripted demo, click `Load morning rush` on the operations dashboard.
4. Use the live map and summary metrics to explain reduced waiting and better van occupancy.

## Important API Endpoints

- `GET /api/stops`
- `POST /api/requests`
- `GET /api/requests`
- `GET /api/routes`
- `GET /api/vehicles`
- `GET /api/dashboard/summary`
- `POST /api/dispatch/run`
- `POST /api/demo/reset`
- `POST /api/demo/scenario/morning-rush`
