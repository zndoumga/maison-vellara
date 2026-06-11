'use client'

import { useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { supabase } from '@/lib/supabase'
import { fetchEcomOrders } from '@/lib/api'
import { format, subDays } from 'date-fns'

interface DayData {
  date: string
  boutique: number
  online: number
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-obsidian-card border border-obsidian-border p-3 text-xs font-mono">
      <p className="text-gold-dim mb-2">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>{p.name}: {p.value}</p>
      ))}
    </div>
  )
}

export default function SalesChart() {
  const [data, setData] = useState<DayData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      const days = Array.from({ length: 7 }, (_, i) => {
        const d = subDays(new Date(), 6 - i)
        return format(d, 'yyyy-MM-dd')
      })

      // Boutique: count SALE transactions per day from Supabase
      const { data: posData } = await supabase
        .schema('pos')
        .from('transactions')
        .select('transaction_date')
        .eq('transaction_type', 'SALE')
        .in('transaction_date', days)

      const boutiqueCounts: Record<string, number> = {}
      days.forEach(d => boutiqueCounts[d] = 0)
      posData?.forEach(r => {
        const d = r.transaction_date
        if (boutiqueCounts[d] !== undefined) boutiqueCounts[d]++
      })

      // Online: fetch from FastAPI
      const onlineCounts: Record<string, number> = {}
      await Promise.all(
        days.map(async d => {
          const orders = await fetchEcomOrders(d)
          onlineCounts[d] = Array.isArray(orders) ? orders.length : 0
        })
      )

      setData(days.map(d => ({
        date: format(new Date(d + 'T12:00:00'), 'MMM d'),
        boutique: boutiqueCounts[d] ?? 0,
        online: onlineCounts[d] ?? 0,
      })))
      setLoading(false)
    }
    load()
  }, [])

  return (
    <div className="card p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-xs tracking-[0.2em] uppercase text-gold-dim">Sales Volume — Last 7 Days</span>
        <div className="flex gap-4 text-[10px] font-mono">
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-gold inline-block" />Boutique</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-blue-400 inline-block" />Online</span>
        </div>
      </div>

      {loading ? (
        <div className="h-40 bg-obsidian-muted/20 rounded animate-pulse" />
      ) : (
        <ResponsiveContainer width="100%" height={160}>
          <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
            <defs>
              <linearGradient id="boutiqueGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#B8924A" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#B8924A" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="onlineGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1C1C1C" />
            <XAxis dataKey="date" tick={{ fill: '#7A5F2E', fontSize: 10, fontFamily: 'var(--font-dm-mono)' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#7A5F2E', fontSize: 10, fontFamily: 'var(--font-dm-mono)' }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey="boutique" stroke="#B8924A" strokeWidth={1.5} fill="url(#boutiqueGrad)" dot={false} />
            <Area type="monotone" dataKey="online" stroke="#60a5fa" strokeWidth={1.5} fill="url(#onlineGrad)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
