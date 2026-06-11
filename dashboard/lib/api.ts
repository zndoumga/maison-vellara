const BASE = process.env.NEXT_PUBLIC_API_URL ?? ''
const KEY  = process.env.NEXT_PUBLIC_API_KEY  ?? ''

const headers = { 'x-api-key': KEY }

export async function fetchEcomOrders(date: string) {
  try {
    const r = await fetch(`${BASE}/ecom/orders?date=${date}`, { headers, next: { revalidate: 60 } })
    if (!r.ok) return []
    return r.json()
  } catch { return [] }
}

export async function fetchSellthrough(partner: string, date: string) {
  try {
    const r = await fetch(`${BASE}/wholesale/${partner}/sellthrough?date=${date}`, { headers, next: { revalidate: 60 } })
    if (r.status === 404) return null        // portal outage
    if (!r.ok) return null
    return r.json()
  } catch { return null }
}
