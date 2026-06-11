'use client'
import { useEffect, useState, useCallback } from 'react'
import { fetchEcomOrders, fetchEcomEvents, fetchEcomReturns } from '@/lib/api'
import { format } from 'date-fns'
import PageHeader from '@/components/PageHeader'

export default function OnlinePage() {
  const [date, setDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [orders, setOrders] = useState<any[]>([])
  const [events, setEvents] = useState<any[]>([])
  const [returns, setReturns] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    const [o, e, r] = await Promise.all([fetchEcomOrders(date), fetchEcomEvents(date), fetchEcomReturns(date)])
    setOrders(o); setEvents(e); setReturns(r); setLoading(false)
  }, [date])
  useEffect(() => { load() }, [load])

  const funnel = {
    sessions: new Set(events.map((e: any) => e.session_id)).size,
    views: events.filter((e: any) => e.event_type === 'product_view').length,
    carts: events.filter((e: any) => e.event_type === 'add_to_cart').length,
    checkouts: events.filter((e: any) => e.event_type === 'checkout_completed').length,
  }
  const revenue = orders.filter(o => o.financial_status === 'paid').reduce((s, o) => s + (o.total ?? 0), 0)

  return (
    <div className="p-6 md:p-8 max-w-[1400px] mx-auto">
      <PageHeader title="Online Store" subtitle="Source 2 · FastAPI / Firebase (nested JSON)" />

      <div className="flex flex-wrap gap-3 mb-4 items-center">
        <input type="date" value={date} onChange={e => setDate(e.target.value)} min="2026-01-01"
          className="bg-white border border-paper-border rounded-sm px-3 py-1.5 text-xs font-mono text-ink" />
        <span className="text-xs text-ink-faint font-mono ml-auto">via {process.env.NEXT_PUBLIC_API_URL?.replace('https://', '')}</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        {[
          { l: 'Orders', v: orders.length },
          { l: 'Revenue', v: `€${revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
          { l: 'Sessions', v: funnel.sessions },
          { l: 'Returns', v: returns.length },
        ].map((k, i) => (
          <div key={i} className="card-gold p-4">
            <span className="text-[10px] tracking-[0.2em] uppercase text-ink-faint">{k.l}</span>
            <p className="text-2xl font-light text-ink font-mono mt-1">{loading ? '—' : k.v}</p>
          </div>
        ))}
      </div>

      {/* Funnel */}
      <div className="card p-5 mb-4">
        <span className="text-[10px] tracking-[0.2em] uppercase text-ink-faint">Conversion Funnel — {date}</span>
        <div className="flex items-end gap-2 mt-4 h-24">
          {[
            { l: 'Sessions', v: funnel.sessions },
            { l: 'Product Views', v: funnel.views },
            { l: 'Add to Cart', v: funnel.carts },
            { l: 'Checkouts', v: funnel.checkouts },
          ].map((step, i) => {
            const max = funnel.sessions || 1
            return (
              <div key={i} className="flex-1 flex flex-col items-center justify-end gap-2">
                <span className="text-xs font-mono text-ink">{step.v}</span>
                <div className="w-full bg-gold/70 rounded-t-sm transition-all" style={{ height: `${Math.max((step.v / max) * 100, 2)}%` }} />
                <span className="text-[10px] text-ink-faint text-center">{step.l}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Orders table */}
      <div className="card overflow-x-auto">
        <div className="px-5 py-4 border-b border-paper-border">
          <span className="text-[10px] tracking-[0.2em] uppercase text-ink-faint">Orders — click to expand line items</span>
        </div>
        <table>
          <thead><tr>
            <th>Order ID</th><th>Customer</th><th>Country</th><th>Channel</th><th>Device</th>
            <th>Status</th><th className="text-right">Total</th><th>Time</th>
          </tr></thead>
          <tbody>
            {loading ? (
              [...Array(8)].map((_, i) => <tr key={i}><td colSpan={8}><div className="h-5 bg-paper rounded animate-pulse" /></td></tr>)
            ) : orders.length === 0 ? (
              <tr><td colSpan={8} className="text-center text-ink-faint py-6">No orders for this date</td></tr>
            ) : orders.map((o: any) => (
              <>
                <tr key={o.order_id} className="cursor-pointer" onClick={() => setExpanded(expanded === o.order_id ? null : o.order_id)}>
                  <td className="text-ink-faint">{o.order_id}</td>
                  <td className="text-ink whitespace-nowrap">{o.client?.first_name} {o.client?.last_name}</td>
                  <td className="text-ink-muted">{o.shipping_address?.country}</td>
                  <td className="text-ink-faint">{o.channel}</td>
                  <td className="text-ink-faint">{o.device_type}</td>
                  <td><span className={`text-[10px] px-1.5 py-0.5 rounded border ${o.financial_status === 'paid' ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : 'text-red-600 bg-red-50 border-red-200'}`}>{o.financial_status}</span></td>
                  <td className="text-right font-medium text-ink whitespace-nowrap">€{Number(o.total).toLocaleString()}</td>
                  <td className="text-ink-faint">{o.created_at?.slice(11, 16)}</td>
                </tr>
                {expanded === o.order_id && (
                  <tr key={o.order_id + '-exp'}>
                    <td colSpan={8} className="bg-paper">
                      <div className="text-[11px] font-mono text-ink-muted py-1">
                        {o.line_items?.map((li: any) => (
                          <div key={li.line_id} className="flex gap-4 py-0.5">
                            <span className="text-gold">{li.sku_id}</span>
                            <span>{li.product_name}</span>
                            <span>×{li.quantity}</span>
                            <span className="ml-auto">€{Number(li.unit_price).toLocaleString()}</span>
                          </div>
                        ))}
                        <div className="text-ink-faint mt-1">{o.client?.email} · {o.shipping_address?.city}, {o.shipping_address?.zip}</div>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
