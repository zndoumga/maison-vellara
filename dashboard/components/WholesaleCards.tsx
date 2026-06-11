'use client'

import { useEffect, useState } from 'react'
import { fetchSellthrough } from '@/lib/api'
import { format } from 'date-fns'

interface PartnerData {
  id: string
  name: string
  units: number | null
  revenue: number | null
  available: boolean
}

function extractSellthrough(partner: string, data: any): { units: number; revenue: number } {
  if (!data) return { units: 0, revenue: 0 }

  if (partner === 'glf') {
    const items = data.items ?? []
    return {
      units: items.reduce((s: number, i: any) => s + (i.qty_sold_today ?? 0), 0),
      revenue: items.reduce((s: number, i: any) => s + (i.revenue_eur ?? 0), 0),
    }
  }
  if (partner === 'lbm') {
    const sales = data.sales ?? {}
    return {
      units: Object.values(sales).reduce((s: number, v: any) => s + (v.units ?? 0), 0),
      revenue: Object.values(sales).reduce((s: number, v: any) => s + (v.ca_eur ?? 0), 0),
    }
  }
  // prt — array
  const rows = Array.isArray(data) ? data : []
  return {
    units: rows.reduce((s: number, r: any) => s + (r.vte ?? 0), 0),
    revenue: rows.reduce((s: number, r: any) => s + (r.ca ?? 0), 0),
  }
}

export default function WholesaleCards() {
  const today = format(new Date(), 'yyyy-MM-dd')
  const [partners, setPartners] = useState<PartnerData[]>([
    { id: 'glf', name: 'Galeries Lafayette', units: null, revenue: null, available: true },
    { id: 'lbm', name: 'Le Bon Marché',      units: null, revenue: null, available: true },
    { id: 'prt', name: 'Printemps',           units: null, revenue: null, available: true },
  ])

  useEffect(() => {
    Promise.all(
      partners.map(async (p) => {
        const data = await fetchSellthrough(p.id, today)
        if (data === null) return { ...p, available: false }
        const { units, revenue } = extractSellthrough(p.id, data)
        return { ...p, units, revenue, available: true }
      })
    ).then(setPartners)
  }, [today])

  return (
    <div className="flex flex-col gap-4">
      <span className="text-xs tracking-[0.2em] uppercase text-gold-dim">Wholesale Sell-Through — Today</span>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {partners.map((p) => (
          <div key={p.id} className={`card p-4 flex flex-col gap-3 ${!p.available ? 'opacity-50' : ''}`}>
            <div className="flex items-center justify-between">
              <span className="text-xs text-cream/50 font-mono truncate">{p.name}</span>
              <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${p.available ? 'bg-emerald-400' : 'bg-obsidian-muted'}`} />
            </div>

            {!p.available ? (
              <p className="text-[10px] text-obsidian-muted font-mono">Portal unavailable</p>
            ) : p.units === null ? (
              <div className="h-8 bg-obsidian-muted/30 rounded animate-pulse" />
            ) : (
              <div className="flex flex-col gap-1">
                <div className="flex items-end gap-1.5">
                  <span className="text-3xl font-light text-cream font-mono">{p.units}</span>
                  <span className="text-xs text-gold-dim mb-1">units sold</span>
                </div>
                <span className="text-xs text-obsidian-muted font-mono">
                  {p.revenue !== null ? `€${p.revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })} revenue` : ''}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
