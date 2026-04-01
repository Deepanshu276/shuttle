import type {
  DashboardSummary,
  DemoScenario,
  DispatchRunResult,
  RideRequest,
  RideRequestPayload,
  Route,
  StopsCatalog,
  Vehicle,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || 'Request failed')
  }

  return (await response.json()) as T
}

export const api = {
  getStops: () => request<StopsCatalog>('/stops'),
  getRequests: () => request<RideRequest[]>('/requests'),
  getRequest: (requestId: string) => request<RideRequest>(`/requests/${requestId}`),
  getRoutes: () => request<Route[]>('/routes'),
  getVehicles: () => request<Vehicle[]>('/vehicles'),
  getSummary: () => request<DashboardSummary>('/dashboard/summary'),
  createRequest: (payload: RideRequestPayload) =>
    request<RideRequest>('/requests', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  runDispatch: () =>
    request<DispatchRunResult>('/dispatch/run', {
      method: 'POST',
    }),
  resetDemo: () =>
    request<DemoScenario>('/demo/reset', {
      method: 'POST',
    }),
  loadMorningRush: () =>
    request<DemoScenario>('/demo/scenario/morning-rush', {
      method: 'POST',
    }),
  reoptimizeRoute: (routeId: number) =>
    request<Route>(`/routes/${routeId}/reoptimize`, { method: 'POST' }),
}
