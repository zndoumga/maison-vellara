const BASE = process.env.NEXT_PUBLIC_API_URL ?? ''
const KEY  = process.env.NEXT_PUBLIC_API_KEY  ?? ''
const headers = { 'x-api-key': KEY }

async function get(path: string) {
  try {
    const r = await fetch(`${BASE}${path}`, { headers })
    if (r.status === 404) return null
    if (!r.ok) return null
    return r.json()
  } catch { return null }
}

export async function fetchEcomOrders(date: string) {
  const d = await get(`/ecom/orders?date=${date}`)
  return Array.isArray(d) ? d : []
}
export async function fetchEcomEvents(date: string) {
  const d = await get(`/ecom/events?date=${date}`)
  return Array.isArray(d) ? d : []
}
export async function fetchEcomReturns(date: string) {
  const d = await get(`/ecom/returns?date=${date}`)
  return Array.isArray(d) ? d : []
}
export async function fetchSellthrough(partner: string, date: string) {
  return get(`/wholesale/${partner}/sellthrough?date=${date}`)
}
