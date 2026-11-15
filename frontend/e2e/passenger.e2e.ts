import { expect, test } from '@playwright/test'

test('searches a prepared journey and opens its scheduled stops', async ({ page }) => {
  await page.goto('/')

  await page.getByLabel('Departure station').selectOption({ label: 'Jaffna' })
  await page.getByLabel('Arrival station').selectOption({ label: 'Colombo Fort' })
  await page.getByLabel('Travel date').fill('2026-11-16')
  await page.getByRole('button', { name: 'Search journeys', exact: true }).click()

  const results = page.getByRole('region', { name: 'Journey results' })
  await expect(
    results.getByRole('heading', { name: 'Demo Northern Return' }),
  ).toBeVisible()

  await results.getByRole('button', {
    name: 'View journey details for Demo Northern Return',
  }).click()

  const details = page.getByRole('region', { name: 'Journey details' })
  await expect(details.getByRole('heading', { name: /Stop 1: Jaffna/ })).toBeVisible()
  await expect(details.getByRole('heading', { name: /Stop 4: Colombo Fort/ })).toBeVisible()
  await expect(details.locator('time[datetime="2026-11-16T16:00:00+05:30"]')).toBeVisible()
})

test('restores cited assistant history and denies access to a second guest', async ({
  page,
  browser,
}) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Passenger assistant', exact: true }).click()
  await page.getByLabel('Question').fill('How do I report a disruption?')

  const creation = page.waitForResponse((response) =>
    new URL(response.url()).pathname === '/api/v1/assistant/conversations' &&
    response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Send', exact: true }).click()

  const created = await creation
  expect(created.status()).toBe(201)
  const { conversation_id: id } = await created.json() as { conversation_id: string }

  const citation = /RailConnect passenger guide v1.*report-disruption/
  await expect(page.getByText(citation)).toBeVisible()

  await page.reload()
  await page.getByRole('button', { name: 'Passenger assistant', exact: true }).click()
  await expect(page.getByText(citation)).toBeVisible()

  const otherGuest = await browser.newContext()
  try {
    const response = await otherGuest.request.get(`${created.url()}/${id}`)
    expect(response.status()).toBe(404)
  } finally {
    await otherGuest.close()
  }
})

test('supports keyboard navigation and passenger forms at a narrow width', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')

  const navigation = page.getByRole('navigation', { name: 'Application sections' })
  await expect(page.getByLabel('Departure station')).toBeEnabled()

  await page.keyboard.press('Tab')
  await expect(navigation.getByRole('button', { name: 'Journey search' })).toBeFocused()

  await page.keyboard.press('Tab')
  const assistant = navigation.getByRole('button', { name: 'Passenger assistant' })
  await expect(assistant).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByLabel('Question')).toBeVisible()

  const fitsViewport = () =>
    page.locator('html').evaluate((root) => root.scrollWidth <= root.clientWidth)

  await expect.poll(fitsViewport).toBe(true)

  const report = navigation.getByRole('button', { name: 'Report a disruption' })
  await report.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByLabel('Report title')).toBeVisible()
  await expect.poll(fitsViewport).toBe(true)
})
