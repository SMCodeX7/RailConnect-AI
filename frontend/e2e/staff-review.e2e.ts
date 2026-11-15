import { env } from 'node:process'
import { expect, test } from '@playwright/test'

const TRAVEL_DATE = '2026-11-16'
const SCHEDULED_ARRIVAL = `${TRAVEL_DATE}T16:00:00+05:30`
const ESTIMATED_ARRIVAL = `${TRAVEL_DATE}T16:15:00+05:30`
const DETAIL_PATH = new RegExp('^/api/v1/journeys/[0-9a-f-]{36}$', 'i')

function recentColomboTime(): string {
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Colombo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  })
    .format(new Date(Date.now() - 120_000))
    .replace(' ', 'T')
}

test('controller verifies a delay and the existing journey refreshes', async ({
  page,
  browser,
  baseURL,
}) => {
  test.setTimeout(60_000)

  const username = env.RAILCONNECT_E2E_CONTROLLER
  const password = env.RAILCONNECT_E2E_PASSWORD
  if (!username || !password) {
    throw new Error('Set the local controller username and password before running this test.')
  }

  await page.goto('/')
  await page.getByLabel('Departure station').selectOption({ label: 'Jaffna' })
  await page.getByLabel('Arrival station').selectOption({ label: 'Colombo Fort' })
  await page.getByLabel('Travel date').fill(TRAVEL_DATE)
  await page.getByRole('button', { name: 'Search journeys', exact: true }).click()

  const originalDetail = page.waitForResponse((response) =>
    DETAIL_PATH.test(new URL(response.url()).pathname),
  )
  await page.getByRole('button', {
    name: 'View journey details for Demo Northern Return',
  }).click()

  const original = await originalDetail
  expect(original.status()).toBe(200)
  const runId = new URL(original.url()).pathname.split('/').at(-1)
  if (!runId) throw new Error('Journey details did not include a run ID.')

  const details = page.getByRole('region', { name: 'Journey details' })
  await expect(details.locator(`time[datetime="${SCHEDULED_ARRIVAL}"]`)).toBeVisible()

  const staffContext = await browser.newContext({
    baseURL,
    viewport: { width: 390, height: 844 },
  })

  try {
    const staff = await staffContext.newPage()
    const title = `Synthetic Playwright delay ${Date.now()}`

    await staff.goto('/')
    await staff.getByRole('button', { name: 'Report a disruption', exact: true }).click()
    await staff.getByLabel('Report title').fill(title)
    await staff.getByLabel('Describe what you observed').fill('Local browser test of a 15-minute delay.')
    await staff.getByLabel('Observation date and time').fill(recentColomboTime())
    await staff.getByRole('button', { name: 'Submit report', exact: true }).click()
    await expect(staff.getByText('Report received. Its status is pending staff review.')).toBeVisible()

    await staff.getByRole('button', { name: 'Staff access', exact: true }).click()
    await staff.getByLabel('Staff username').fill(username)
    await staff.getByLabel('Password').fill(password)
    await staff.getByRole('button', { name: 'Sign in', exact: true }).click()

    await staff.getByRole('button', { name: 'Load pending reports' }).click()
    await expect(staff.getByRole('heading', { name: 'Timetable import', exact: true })).toHaveCount(0)

    const report = staff.getByRole('listitem').filter({
      has: staff.getByRole('heading', { name: title, exact: true }),
    })
    await report.getByRole('button', { name: 'Open report review' }).click()

    await staff.getByLabel('Decision', { exact: true }).selectOption('verify')
    await staff.getByLabel('Decision reason').fill('Verify a synthetic Playwright delay.')
    await staff.getByLabel('Approved dated run ID').fill(runId)
    await staff.getByLabel('Approved scope', { exact: true }).selectOption('run')
    await staff.getByLabel('Approved impact', { exact: true }).selectOption('delay')
    await staff.getByLabel('Approved estimated delay in minutes').fill('15')
    await staff.getByLabel(/Effective start/).fill(`${TRAVEL_DATE}T06:00`)
    await staff.getByLabel(/Effective end/).fill(`${TRAVEL_DATE}T17:00`)
    await staff.getByLabel('Approved public summary').fill('Synthetic 15-minute browser test delay.')
    await staff.getByLabel('Private evidence basis').fill('Controlled local test fixture.')

    const confirmation = staff.getByRole('checkbox', { name: /I independently reviewed/ })
    await expect(confirmation).toBeVisible()
    const checkboxBox = await confirmation.boundingBox()
    expect(checkboxBox?.width ?? 0).toBeGreaterThan(0)
    expect(checkboxBox?.width ?? 0).toBeLessThan(28)
    await confirmation.focus()
    await confirmation.press('Space')
    await expect(confirmation).toBeChecked()

    const verification = staff.waitForResponse((response) =>
      new URL(response.url()).pathname.endsWith('/verify') &&
      response.request().method() === 'POST',
    )
    await staff.getByRole('button', { name: 'Verify report', exact: true }).click()

    const verified = await verification
    expect(verified.status()).toBe(200)
    const { incident_id: incidentId } = await verified.json() as { incident_id: string }
    expect(incidentId).toBeTruthy()

    const refreshedDetail = page.waitForResponse((response) =>
      new URL(response.url()).pathname === `/api/v1/journeys/${runId}`,
    )
    await details.getByRole('button', { name: 'Refresh journey details' }).click()

    const refreshed = await refreshedDetail
    expect(refreshed.status()).toBe(200)
    const body = await refreshed.json() as {
      selected_segment: { disruption: { effects: { incident_id: string }[] } }
    }
    expect(body.selected_segment.disruption.effects).toContainEqual(
      expect.objectContaining({ incident_id: incidentId }),
    )

    await expect(details.locator(`time[datetime="${SCHEDULED_ARRIVAL}"]`)).toBeVisible()
    await expect(details.locator(`time[datetime="${ESTIMATED_ARRIVAL}"]`)).toBeVisible()

    await page.getByRole('button', { name: 'Refresh journey results' }).click()
    const results = page.getByRole('region', { name: 'Journey results' })
    await expect(results.locator(`time[datetime="${ESTIMATED_ARRIVAL}"]`)).toBeVisible()
    const management = staff.getByRole('region', {
      name: 'Manage a verified incident',
    })
    await management.getByLabel('Incident reference', { exact: true }).fill(incidentId)
    await management.getByRole('button', { name: 'Load current incident' }).click()
    await management.getByLabel('Lifecycle action', { exact: true }).selectOption('amend')

    const amendmentCheckbox = management.getByRole('checkbox', {
      name: /I independently reviewed the complete replacement facts/,
    })
    await expect(amendmentCheckbox).toBeVisible()
    const amendmentBox = await amendmentCheckbox.boundingBox()
    expect(amendmentBox?.width ?? 0).toBeGreaterThan(0)
    expect(amendmentBox?.width ?? 0).toBeLessThan(28)

    await amendmentCheckbox.focus()
    await expect(amendmentCheckbox).toBeFocused()
    await amendmentCheckbox.press('Space')
    await expect(amendmentCheckbox).toBeChecked()
  } finally {
    await staffContext.close()
  }
})
