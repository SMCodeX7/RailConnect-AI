import { useState } from 'react'

import { PassengerAssistant } from './features/assistant/components/PassengerAssistant'
import { StaffPanel } from './features/auth/components/StaffPanel'
import { PassengerReportForm } from './features/incidents/components/PassengerReportForm'
import { JourneyStationPicker } from './features/journeys/components/JourneyStationPicker'
import './release.css'

const navigation = [
  { page: 'journeys', label: 'Journey search' },
  { page: 'assistant', label: 'Passenger assistant' },
  { page: 'report', label: 'Report a disruption' },
  { page: 'staff', label: 'Staff access' },
] as const

type Page = (typeof navigation)[number]['page']

export default function App() {
  const [page, setPage] = useState<Page>('journeys')

  return (
    <>
      <header className="app-masthead">
        <div className="app-masthead-inner">
          <h1 className="app-wordmark">RailConnect AI</h1>

          <nav className="app-navigation" aria-label="Application sections">
            {navigation.map((item) => (
              <button
                key={item.page}
                type="button"
                aria-pressed={page === item.page}
                onClick={() => setPage(item.page)}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <p className="app-data-notice">
        Demonstration data for selected Sri Lankan stations. Live updates are unavailable.
      </p>

      <main className="app-shell">
        {page === 'journeys' && <JourneyStationPicker />}
        {page === 'assistant' && <PassengerAssistant />}
        {page === 'report' && <PassengerReportForm />}
        {page === 'staff' && <StaffPanel />}
      </main>
    </>
  )
}
