'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

interface Alert {
  store_id: string
  sku_id: string
  qty_on_hand: number
  snapshot_ts: string
}

const STORE_NAMES: Record<string, string> = {
  ST001: 'Paris Faubourg', ST002: 'Paris Marais', ST003: 'London Mayfair',
  ST004: 'Milan', ST005: 'Dubai', ST006: 'Tokyo', ST007: 'New York', ST008: 'Geneva',
}

export default function InventoryAlerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase
      .schema('inventory')
      .from('snapshots')
      .select('store_id,sku_id,qty_on_hand,snapshot_ts')
      .eq('reorder_flag', true)
      .order('snapshot_ts', { ascending: false })
      .limit(40)
      .then(({ data }) => {
        if (data) {
          // deduplicate to latest per store+sku
          const seen = new Set<string>()
          const deduped: Alert[] = []
          for (const row of data as Alert[]) {
            const key = `${row.store_id}:${row.sku_id}`
            if (!seen.has(key)) { seen.add(key); deduped.push(row) }
          }
          setAlerts(deduped.slice(0, 10))
        }
        setLoading(false)
      })
  }, [])

  return (
    <div className="card p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-xs tracking-[0.2em] uppercase text-gold-dim">Inventory Reorder Alerts</span>
        {!loading && (
          <span className={`text-xs font-mono ${alerts.length > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
            {alerts.length} active
          </span>
        )}
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => <div key={i} className="h-8 bg-obsidian-muted/30 rounded animate-pulse" />)}
        </div>
      ) : alerts.length === 0 ? (
        <div className="flex items-center gap-2 py-3">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
          <p className="text-xs text-emerald-400/70">All stock levels nominal</p>
        </div>
      ) : (
        <div className="space-y-[2px]">
          {alerts.map((a) => (
            <div key={`${a.store_id}-${a.sku_id}`}
              className="flex items-center gap-3 px-3 py-2 text-xs font-mono border border-red-900/20 bg-red-950/10 rounded-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0" />
              <span className="text-cream/60 flex-1 truncate">{STORE_NAMES[a.store_id] ?? a.store_id}</span>
              <span className="text-cream/40 truncate flex-1">{a.sku_id}</span>
              <span className="text-red-400 whitespace-nowrap">{a.qty_on_hand} left</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
