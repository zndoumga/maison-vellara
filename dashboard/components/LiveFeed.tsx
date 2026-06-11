'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

interface Transaction {
  transaction_id: string
  store_id: string
  sku_id: string
  unit_price: number
  currency: string
  transaction_time: string
  transaction_type: 'SALE' | 'RETURN' | 'CORRECTION'
  isNew?: boolean
}

const STORE_NAMES: Record<string, string> = {
  ST001: 'Paris Faubourg', ST002: 'Paris Marais', ST003: 'London Mayfair',
  ST004: 'Milan Montenapoleone', ST005: 'Dubai Mall', ST006: 'Tokyo Ginza',
  ST007: 'New York Madison', ST008: 'Geneva Rhône',
}

const TYPE_STYLE: Record<string, string> = {
  SALE: 'text-emerald-400 border-emerald-400/30',
  RETURN: 'text-amber-400 border-amber-400/30',
  CORRECTION: 'text-yellow-300 border-yellow-300/30',
}

export default function LiveFeed() {
  const [rows, setRows] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Initial fetch — last 12 transactions
    supabase
      .schema('pos')
      .from('transactions')
      .select('transaction_id,store_id,sku_id,unit_price,currency,transaction_time,transaction_type,transaction_date')
      .order('transaction_date', { ascending: false })
      .order('transaction_time', { ascending: false })
      .limit(12)
      .then(({ data }) => {
        if (data) setRows(data as Transaction[])
        setLoading(false)
      })

    // Realtime subscription
    const channel = supabase
      .channel('pos-live')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'pos', table: 'transactions' },
        (payload) => {
          const tx = { ...(payload.new as Transaction), isNew: true }
          setRows((prev) => {
            const next = [tx, ...prev].slice(0, 12)
            // remove isNew after animation
            setTimeout(() => {
              setRows((r) => r.map((t) => (t.transaction_id === tx.transaction_id ? { ...t, isNew: false } : t)))
            }, 600)
            return next
          })
        }
      )
      .subscribe()

    return () => { supabase.removeChannel(channel) }
  }, [])

  return (
    <div className="card p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-xs tracking-[0.2em] uppercase text-gold-dim">Live Boutique Feed</span>
        <span className="text-xs text-obsidian-muted">{rows.length} recent</span>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-8 bg-obsidian-muted/30 rounded animate-pulse" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <p className="text-xs text-obsidian-muted py-4 text-center">No transactions yet today</p>
      ) : (
        <div className="space-y-[2px]">
          {rows.map((tx) => (
            <div
              key={`${tx.transaction_id}-${tx.transaction_time}`}
              className={`flex items-center gap-3 px-3 py-2 rounded-sm text-xs transition-all duration-300 ${
                tx.isNew ? 'animate-slide-in bg-gold/5 border border-gold/10' : 'border border-transparent hover:bg-obsidian-card'
              }`}
            >
              <span className={`border px-1.5 py-0.5 rounded-sm text-[10px] tracking-wider font-mono min-w-[70px] text-center ${TYPE_STYLE[tx.transaction_type] ?? 'text-cream/40'}`}>
                {tx.transaction_type}
              </span>
              <span className="text-cream/60 truncate flex-1 font-mono">
                {STORE_NAMES[tx.store_id] ?? tx.store_id}
              </span>
              <span className="text-cream/40 truncate max-w-[120px] font-mono hidden sm:block">
                {tx.sku_id}
              </span>
              <span className="text-gold font-mono font-medium whitespace-nowrap">
                {Number(tx.unit_price).toLocaleString()} {tx.currency}
              </span>
              <span className="text-obsidian-muted font-mono whitespace-nowrap hidden md:block">
                {tx.transaction_time?.slice(0, 5)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
