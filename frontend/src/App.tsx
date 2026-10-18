import { useState } from 'react'

import { StaffPanel } from './features/auth/components/StaffPanel'
import { PassengerReportForm } from './features/incidents/components/PassengerReportForm'
import { JourneyStationPicker } from './features/journeys/components/JourneyStationPicker'

type Page = 'journeys' | 'report' | 'staff'

export default function App() {
  const [page, setPage] = useState<Page>('journeys')

  return (
    <main className="app-shell">
      <header className="page-header">
        <span className="badge">Portfolio pilot</span>
        <h1>RailConnect AI</h1>
        <p>A clearer way to plan railway journeys across Sri Lanka.</p>
      </header>

      <aside className="demo-notice">
        Demonstration data: selected stations are included for this pilot.
        Live timetables and service updates are not available yet.
      </aside>

      <nav className="app-navigation" aria-label="Application sections">
        <button
          type="button"
          aria-pressed={page === 'journeys'}
          onClick={() => setPage('journeys')}
        >
          Journey search
        </button>

        <button
          type="button"
          aria-pressed={page === 'report'}
          onClick={() => setPage('report')}
        >
          Report a disruption
        </button>

        <button
          type="button"
          aria-pressed={page === 'staff'}
          onClick={() => setPage('staff')}
        >
          Staff access
        </button>
      </nav>

      {page === 'journeys' && <JourneyStationPicker />}
      {page === 'report' && <PassengerReportForm />}
      {page === 'staff' && <StaffPanel />}
    </main>
  )
}
