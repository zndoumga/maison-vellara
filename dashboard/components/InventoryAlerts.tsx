'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

interface Alert { store_id: string; sku_id: string; qty_on_hand: number; snapshot_ts: string }

const STORE: Record<string, string> = {
  ST001:'Paris Faubourg', ST002:'Paris Marais', ST003:'London Mayfair',
  ST004:'Milan', ST005:'Dubai', ST006:'Tokyo', ST007:'New York', ST008:'Geneva',
}

export default function InventoryAlerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.schema('inventory').from('snapshots')
      .select('store_id,sku_id,qty_on_hand,snapshot_ts')
      .eq('reorder_flag', true)
      .order('snapshot_ts', { ascending: false })
      .limit(60)
      .then(({ data }) => {
        if (data) {
          const seen = new Set<string>()
          const deduped: Alert[] = []
          for (const row of data as Alert[]) {
            const key = `${row.store_id}:${row.sku_id}`
            if (!seen.has(key)) { seen.add(key); deduped.push(row) }
          }
          setAlerts(deduped.slice(0, 15))
        }
        setLoading(false)
      })
  }, [])

  return (
    <div className="card flex flex-col">
      <div className="px-5 py-4 border-b border-paper-border flex justify-between items-center">
        <span className="text-[10px] tracking-[0.2em] uppercase text-ink-faint">Inventory Reorder Alerts</span>
        {!loading && <span className={`text-[10px] font-mono ${alerts.length > 0 ? 'text-red-600' : 'text-emerald-600'}`}>{alerts.length} active</span>}
      </div>
      {loading ? (
        <div className="p-4 space-y-2">{[...Array(4)].map((_, i) => <div key={i} className="h-7 bg-paper rounded animate-pulse" />)}</div>
      ) : alerts.length === 0 ? (
        <p className="p-6 text-xs text-emerald-600 text-center">All stock levels nominal</p>
      ) : (
        <div className="overflow-x-auto">
          <table>
            <thead><tr><th>Store</th><th>SKU</th><th className="text-right">On Hand</th><th>Status</th></tr></thead>
            <tbody>
              {alerts.map(a => (
                <tr key={`${a.store_id}-${a.sku_id}`}>
                  <td className="text-ink-muted">{STORE[a.store_id] ?? a.store_id}</td>
                  <td className="text-ink-muted">{a.sku_id}</td>
                  <td className={`text-right font-mono font-medium ${a.qty_on_hand < 0 ? 'text-red-600' : a.qty_on_hand === 0 ? 'text-orange-600' : 'text-amber-600'}`}>
                    {a.qty_on_hand}
                  </td>
                  <td>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${a.qty_on_hand < 0 ? 'text-red-600 bg-red-50 border-red-200' : 'text-amber-700 bg-amber-50 border-amber-200'}`}>
                      {a.qty_on_hand < 0 ? 'OVERALLOCATED' : 'REORDER'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {alerts.some(a => a.qty_on_hand < 0) && (
        <p className="px-5 py-2 text-[10px] text-ink-faint border-t border-paper-border">
          * Negative stock = timing window between sale and replenishment receipt. Expected behaviour.
        </p>
      )}
    </div>
  )
}
