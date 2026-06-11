'use client'
import { useEffect, useState } from 'react'
import { fetchSellthrough } from '@/lib/api'
import { PARTNER_NAMES } from '@/lib/constants'
import { format } from 'date-fns'

interface PartnerData { id: string; units: number | null; revenue: number | null; available: boolean }

export function extractSellthrough(partner: string, data: any): { units: number; revenue: number } {
  if (!data) return { units: 0, revenue: 0 }
  if (partner === 'glf') {
    const items = data.items ?? []
    return { units: items.reduce((s: number, i: any) => s + (i.qty_sold_today ?? 0), 0),
             revenue: items.reduce((s: number, i: any) => s + (i.revenue_eur ?? 0), 0) }
  }
  if (partner === 'lbm') {
    const sales = data.sales ?? {}
    return { units: Object.values(sales).reduce((s: number, v: any) => s + (v.units ?? 0), 0),
             revenue: Object.values(sales).reduce((s: number, v: any) => s + (v.ca_eur ?? 0), 0) }
  }
  const rows = Array.isArray(data) ? data : []
  return { units: rows.reduce((s: number, r: any) => s + (r.vte ?? 0), 0),
           revenue: rows.reduce((s: number, r: any) => s + (r.ca ?? 0), 0) }
}

export default function WholesaleCards() {
  const today = format(new Date(), 'yyyy-MM-dd')
  const [partners, setPartners] = useState<PartnerData[]>([
    { id: 'glf', units: null, revenue: null, available: true },
    { id: 'lbm', units: null, revenue: null, available: true },
    { id: 'prt', units: null, revenue: null, available: true },
  ])

  useEffect(() => {
    Promise.all(partners.map(async p => {
      const data = await fetchSellthrough(p.id, today)
      if (data === null) return { ...p, available: false }
      const { units, revenue } = extractSellthrough(p.id, data)
      return { ...p, units, revenue, available: true }
    })).then(setPartners)
  }, [today])

  return (
    <div className="card flex flex-col">
      <div className="px-5 py-4 border-b border-paper-border">
        <span className="text-[10px] tracking-[0.2em] uppercase text-ink-faint">Wholesale Sell-Through — Today</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-px bg-paper-border">
        {partners.map(p => (
          <div key={p.id} className={`bg-white p-4 flex flex-col gap-3 ${!p.available ? 'opacity-60' : ''}`}>
            <div className="flex items-center justify-between">
              <span className="text-xs text-ink-muted font-mono truncate">{PARTNER_NAMES[p.id.toUpperCase()]}</span>
              <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${p.available ? 'bg-emerald-500' : 'bg-paper-border'}`} />
            </div>
            {!p.available ? (
              <p className="text-[10px] text-ink-faint font-mono">Portal unavailable</p>
            ) : p.units === null ? (
              <div className="h-8 bg-paper rounded animate-pulse" />
            ) : (
              <div className="flex flex-col gap-1">
                <div className="flex items-end gap-1.5">
                  <span className="text-3xl font-light text-ink font-mono">{p.units}</span>
                  <span className="text-[10px] text-gold mb-1">units</span>
                </div>
                <span className="text-[10px] text-ink-faint font-mono">
                  {p.revenue !== null ? `€${p.revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : ''}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
