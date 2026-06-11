'use client'
import { useEffect, useState, useCallback } from 'react'
import { fetchSellthrough } from '@/lib/api'
import { PARTNER_NAMES } from '@/lib/constants'
import { format } from 'date-fns'
import PageHeader from '@/components/PageHeader'

interface NormRow {
  sku: string; units: number; stock: number; revenue: number
  customer: { name: string; email: string; phone: string; country: string }
}

function normalize(partner: string, data: any): NormRow[] {
  if (!data) return []
  if (partner === 'glf') {
    return (data.items ?? []).map((i: any) => ({
      sku: i.sku, units: i.qty_sold_today, stock: i.qty_stock, revenue: i.revenue_eur,
      customer: { name: `${i.client?.client_prenom ?? ''} ${i.client?.client_nom ?? ''}`.trim(),
        email: i.client?.client_email, phone: i.client?.client_telephone, country: i.client?.client_pays },
    }))
  }
  if (partner === 'lbm') {
    return Object.entries(data.sales ?? {}).map(([sku, v]: [string, any]) => ({
      sku, units: v.units, stock: v.stock_remaining, revenue: v.ca_eur,
      customer: { name: `${v.buyer?.first_name ?? ''} ${v.buyer?.last_name ?? ''}`.trim(),
        email: v.buyer?.email_address, phone: v.buyer?.mobile, country: v.buyer?.country_code },
    }))
  }
  return (Array.isArray(data) ? data : []).map((r: any) => ({
    sku: r.art, units: r.vte, stock: r.stk, revenue: r.ca,
    customer: { name: `${r.cli_prenom ?? ''} ${r.cli_nom ?? ''}`.trim(), email: r.cli_mail, phone: r.cli_tel, country: r.cli_pays },
  }))
}

const SCHEMA_NOTE: Record<string, string> = {
  glf: 'Object · items[] · client{client_nom, client_prenom, client_email…}',
  lbm: 'Object · sales{sku: {units, ca_eur, buyer{last_name, email_address…}}}',
  prt: 'Array · [{dt, art, vte, ca, cli_nom, cli_mail…}]',
}

export default function WholesalePage() {
  const [date, setDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [data, setData] = useState<Record<string, { rows: NormRow[]; available: boolean } | null>>({})
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    const out: Record<string, { rows: NormRow[]; available: boolean } | null> = {}
    await Promise.all(['glf', 'lbm', 'prt'].map(async p => {
      const raw = await fetchSellthrough(p, date)
      out[p] = raw === null ? { rows: [], available: false } : { rows: normalize(p, raw), available: true }
    }))
    setData(out); setLoading(false)
  }, [date])
  useEffect(() => { load() }, [load])

  return (
    <div className="p-6 md:p-8 max-w-[1400px] mx-auto">
      <PageHeader title="Wholesale" subtitle="Partner sell-through — Source 3 · Portal APIs (three independent schemas)" />

      <div className="flex flex-wrap gap-3 mb-4 items-center">
        <input type="date" value={date} onChange={e => setDate(e.target.value)} min="2026-01-01"
          className="bg-white border border-paper-border rounded-sm px-3 py-1.5 text-xs font-mono text-ink" />
        <span className="text-xs text-ink-faint font-mono ml-auto">Each partner returns a different JSON shape — normalised client-side</span>
      </div>

      <div className="flex flex-col gap-4">
        {['glf', 'lbm', 'prt'].map(p => {
          const d = data[p]
          const totalUnits = d?.rows.reduce((s, r) => s + (r.units ?? 0), 0) ?? 0
          const totalRev = d?.rows.reduce((s, r) => s + (r.revenue ?? 0), 0) ?? 0
          return (
            <div key={p} className="card">
              <div className="px-5 py-4 border-b border-paper-border flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-3">
                  <span className="text-sm text-ink font-mono">{PARTNER_NAMES[p.toUpperCase()]}</span>
                  <span className="text-[10px] text-ink-faint font-mono px-2 py-0.5 bg-paper rounded border border-paper-border">{SCHEMA_NOTE[p]}</span>
                </div>
                {d && !loading && (
                  d.available
                    ? <span className="text-xs font-mono text-ink-muted">{totalUnits} units · €{totalRev.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                    : <span className="text-xs font-mono text-ink-faint">Portal unavailable</span>
                )}
              </div>
              {loading ? (
                <div className="p-4"><div className="h-16 bg-paper rounded animate-pulse" /></div>
              ) : !d?.available ? (
                <p className="px-5 py-6 text-xs text-ink-faint text-center">No data — portal returned 404 (outage)</p>
              ) : d.rows.length === 0 ? (
                <p className="px-5 py-6 text-xs text-ink-faint text-center">No sales recorded this day</p>
              ) : (
                <div className="overflow-x-auto">
                  <table>
                    <thead><tr>
                      <th>SKU</th><th className="text-right">Units</th><th className="text-right">Stock Left</th>
                      <th className="text-right">Revenue</th><th>End Customer</th><th>Email</th><th>Phone</th><th>Country</th>
                    </tr></thead>
                    <tbody>
                      {d.rows.map((r, i) => (
                        <tr key={r.sku + i}>
                          <td className="text-ink-muted">{r.sku}</td>
                          <td className="text-right text-ink">{r.units}</td>
                          <td className="text-right text-ink-faint">{r.stock}</td>
                          <td className="text-right text-ink whitespace-nowrap">€{Number(r.revenue).toLocaleString()}</td>
                          <td className="text-ink-muted whitespace-nowrap">{r.customer.name}</td>
                          <td className="text-ink-faint">{r.customer.email}</td>
                          <td className="text-ink-faint">{r.customer.phone}</td>
                          <td className="text-ink-faint">{r.customer.country}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )
        })}
      </div>
      <p className="text-[10px] text-ink-faint mt-3 font-mono">
        Note the four mandatory customer fields (name, email, phone, country) appear under different field names in each partner&apos;s payload — reconciled downstream in dbt.
      </p>
    </div>
  )
}
