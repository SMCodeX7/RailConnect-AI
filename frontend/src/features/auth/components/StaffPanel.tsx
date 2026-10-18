import { StaffReportQueue } from '../../incidents/components/StaffReportQueue'
import { useStaffSession } from '../hooks/useStaffSession'
import type { StaffPermission } from '../types'
import { StaffLoginForm } from './StaffLoginForm'

const permissionLabels: Record<StaffPermission, string> = {
  'reports.read': 'View passenger reports',
  'reports.review': 'Review passenger reports',
  'incidents.edit': 'Manage verified incidents',
  'incidents.resolve': 'Resolve verified incidents',
  'timetable.manage': 'Manage timetable imports',
  'audit.read': 'View audit history',
}

function roleLabel(role: string): string {
  if (role === 'controller') return 'Controller'
  if (role === 'administrator') return 'Administrator'
  return role
}

export function StaffPanel() {
  const {
    status,
    session,
    busy,
    error,
    signIn,
    signOut,
    refresh,
    hasPermission,
  } = useStaffSession()

  return (
    <section
      className="staff-panel"
      aria-labelledby="staff-heading"
      aria-busy={status === 'checking' || busy}
    >
      <h2 id="staff-heading">Staff access</h2>

      <p className="muted">
        Individual staff accounts are required for authorized management work.
        Passenger journey search remains available without signing in.
      </p>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {status === 'checking' && (
        <p role="status">Checking your staff session…</p>
      )}

      {status === 'unavailable' && (
        <button type="button" onClick={refresh}>
          Retry session check
        </button>
      )}

      {status === 'guest' && (
        <>
          <StaffLoginForm busy={busy} onSignIn={signIn} />
          <p className="muted">
            Staff accounts are provisioned individually. Contact your
            administrator if you need access.
          </p>
        </>
      )}

      {status === 'authenticated' && session && (
        <>
          <p role="status">
            Signed in as <strong>{session.actor.display_name}</strong>.
          </p>

          <dl className="staff-account-details">
            <div>
              <dt>Username</dt>
              <dd>{session.actor.username}</dd>
            </div>

            <div>
              <dt>Roles</dt>
              <dd>{session.actor.roles.map(roleLabel).join(', ')}</dd>
            </div>

            <div>
              <dt>Session expires</dt>
              <dd>
                <time dateTime={session.expires_at}>
                  {new Intl.DateTimeFormat('en-GB', {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                    timeZone: 'Asia/Colombo',
                  }).format(new Date(session.expires_at))}
                </time>
                {' '}(Asia/Colombo)
              </dd>
            </div>
          </dl>

          <h3>Account permissions</h3>

          <ul>
            {(Object.keys(permissionLabels) as StaffPermission[])
              .filter(hasPermission)
              .map((permission) => (
                <li key={permission}>{permissionLabels[permission]}</li>
              ))}
          </ul>

          <p className="muted">
            Each protected action requires server-side authorization.
            An inactive session may expire before the time shown above.
          </p>

          <div className="staff-actions">
            <button type="button" disabled={busy} onClick={refresh}>
              Refresh session
            </button>

            <button
              type="button"
              disabled={busy}
              onClick={() => void signOut()}
            >
              {busy ? 'Signing out…' : 'Sign out'}
            </button>
          </div>

          {!busy && hasPermission('reports.read') && (
            <StaffReportQueue
              key={session.actor.user_id}
              session={session}
              onSessionInvalid={refresh}
            />
          )}
        </>
      )}
    </section>
  )
}
