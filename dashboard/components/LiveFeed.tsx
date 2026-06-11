'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

interface Transaction {
  transaction_id: string; store_id: string; sku_id: string
  unit_price: number; currency: string; transaction_time: string
  transaction_date: string; transaction_type: 'SALE' | 'RETURN' | 'CORRECTION'
  isNew?: boolean
}

const STORE: Record<string, string> = {
  ST001:'Paris Faubourg', ST002:'Paris Marais', ST003:'London Mayfair',
  ST004:'Milan', ST005:'Dubai Mall', ST006:'Tokyo Ginza',
  ST007:'New York Madison', ST008:'Geneva Rhône',
}
const TYPE: Record<string, string> = {
  SALE: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  RETURN: 'text-amber-700 bg-amber-50 border-amber-200',
  CORRECTION: 'text-yellow-700 bg-yellow-50 border-yellow-200',
}

export default function LiveFeed() {
  const [rows, setRows] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.schema('pos').from('transactions')
      .select('transaction_id,store_id,sku_id,unit_price,currency,transaction_time,transaction_date,transaction_type')
      .order('transaction_date', { ascending: false })
      .order('transaction_time', { ascending: false })
      .limit(15)
      .then(({ data }) => { if (data) setRows(data as Transaction[]); setLoading(false) })

    const ch = supabase.channel('pos-live')
      .on('postgres_changes', { event: 'INSERT', schema: 'pos', table: 'transactions' }, (p) => {
        const tx = { ...(p.new as Transaction), isNew: true }
        setRows(prev => {
          const next = [tx, ...prev].slice(0, 15)
          setTimeout(() => setRows(r => r.map(t => t.transaction_id === tx.transaction_id ? { ...t, isNew: false } : t)), 600)
          return next
        })
      }).subscribe()
    return () => { supabase.removeChannel(ch) }
  }, [])

  return (
    <div className="card flex flex-col">
      <div className="px-5 py-4 border-b border-paper-border flex justify-between items-center">
        <span className="text-[10px] tracking-[0.2em] uppercase text-ink-faint">Live Boutique Feed</span>
        <span className="text-[10px] text-ink-faint">{rows.length} recent</span>
      </div>
      {loading ? (
        <div className="p-4 space-y-2">{[...Array(6)].map((_, i) => <div key={i} className="h-8 bg-paper rounded animate-pulse" />)}</div>
      ) : rows.length === 0 ? (
        <p className="p-6 text-xs text-ink-faint text-center">No transactions yet</p>
      ) : (
        <div className="overflow-x-auto">
          <table>
            <thead><tr>
              <th>Type</th><th>Store</th><th>SKU</th>
              <th className="text-right">Amount</th><th>Date</th><th>Time</th>
            </tr></thead>
            <tbody>
              {rows.map(tx => (
                <tr key={`${tx.transaction_id}-${tx.transaction_time}`}
                  className={tx.isNew ? 'animate-slide-in bg-gold/5' : ''}>
                  <td><span className={`border px-1.5 py-0.5 rounded-sm text-[10px] tracking-wider ${TYPE[tx.transaction_type] ?? 'text-ink-faint'}`}>{tx.transaction_type}</span></td>
                  <td className="text-ink-muted">{STORE[tx.store_id] ?? tx.store_id}</td>
                  <td className="text-ink-muted max-w-[140px] truncate">{tx.sku_id}</td>
                  <td className="text-right font-mono text-ink">{Number(tx.unit_price).toLocaleString()} <span className="text-ink-faint">{tx.currency}</span></td>
                  <td className="text-ink-faint whitespace-nowrap">{tx.transaction_date}</td>
                  <td className="text-ink-faint whitespace-nowrap">{tx.transaction_time?.slice(0,5)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
