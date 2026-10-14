import { useState } from 'react'
import type { FormEvent } from 'react'

import type { StaffLoginInput } from '../types'

interface StaffLoginFormProps {
  busy: boolean
  onSignIn: (input: StaffLoginInput) => Promise<void>
}

export function StaffLoginForm({
  busy,
  onSignIn,
}: StaffLoginFormProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy || !username.trim() || !password) return

    const input = { username: username.trim(), password }
    setPassword('')
    await onSignIn(input)
  }

  return (
    <form onSubmit={handleSubmit}>
      <fieldset className="staff-login-fields" disabled={busy}>
        <legend>Staff sign-in</legend>

        <div className="field">
          <label htmlFor="staff-username">Staff username</label>
          <input
            id="staff-username"
            name="username"
            autoComplete="username"
            value={username}
            maxLength={64}
            required
            onChange={(event) => setUsername(event.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="staff-password">Password</label>
          <input
            id="staff-password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            maxLength={128}
            required
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>

        <button
          type="submit"
          disabled={busy || !username.trim() || !password}
        >
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </fieldset>
    </form>
  )
}
