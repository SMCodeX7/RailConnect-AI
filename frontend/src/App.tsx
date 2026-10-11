import { JourneyStationPicker } from './features/journeys/components/JourneyStationPicker'

export default function App() {
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

      <JourneyStationPicker />
    </main>
  )
}
