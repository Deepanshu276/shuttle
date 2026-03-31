import { Navigate, NavLink, Route, Routes } from 'react-router-dom'

import './App.css'
import { OpsPage } from './pages/OpsPage'
import { RiderPage } from './pages/RiderPage'

function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Corporate Shuttle MVP</p>
          <h1>Demand-responsive van pooling for campus commuters</h1>
        </div>
        <nav className="nav-tabs" aria-label="Primary">
          <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/rider">
            Rider
          </NavLink>
          <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/ops">
            Operations
          </NavLink>
        </nav>
      </header>

      <main className="app-content">
        <Routes>
          <Route path="/" element={<Navigate replace to="/rider" />} />
          <Route path="/rider" element={<RiderPage />} />
          <Route path="/ops" element={<OpsPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
