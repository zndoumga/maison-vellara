'use client'
import { useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { supabase } from '@/lib/supabase'
import { fetchEcomOrders } from '@/lib/api'
import { format, subDays } from 'date-fns'

interface DayData { date: string; boutique: number; online: number }

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-paper-border p-3 text-xs font-mono shadow-sm">
      <p className="text-ink-faint mb-2">{label}</p>
      {payload.map((p: any) => <p key={p.name} style={{ color: p.color }}>{p.name}: {p.value}</p>)}
    </div>
  )
}

export default function SalesChart() {
  const [data, setData] = useState<DayData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      const days = Array.from({ length: 14 }, (_, i) => format(subDays(new Date(), 13 - i), 'yyyy-MM-dd'))
      const { data: posData } = await supabase.schema('pos').from('transactions')
        .select('transaction_date').eq('transaction_type', 'SALE').in('transaction_date', days)
      const boutique: Record<string, number> = {}
      days.forEach(d => boutique[d] = 0)
      posData?.forEach(r => { if (boutique[r.transaction_date] !== undefined) boutique[r.transaction_date]++ })
      const online: Record<string, number> = {}
      await Promise.all(days.map(async d => {
        const orders = await fetchEcomOrders(d)
        online[d] = Array.isArray(orders) ? orders.length : 0
      }))
      setData(days.map(d => ({ date: format(new Date(d + 'T12:00:00'), 'MMM d'), boutique: boutique[d] ?? 0, online: online[d] ?? 0 })))
      setLoading(false)
    }
    load()
  }, [])

  return (
    <div className="card flex flex-col">
      <div className="px-5 py-4 border-b border-paper-border flex justify-between items-center">
        <span className="text-[10px] tracking-[0.2em] uppercase text-ink-faint">Sales Volume — Last 14 Days</span>
        <div className="flex gap-4 text-[10px] font-mono">
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-gold inline-block" />Boutique</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-blue-400 inline-block" />Online</span>
        </div>
      </div>
      <div className="p-4">
        {loading ? <div className="h-48 bg-paper rounded animate-pulse" /> : (
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#B8924A" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#B8924A" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="og" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.12} />
                  <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E8E3D8" />
              <XAxis dataKey="date" tick={{ fill: '#9A8E7E', fontSize: 10, fontFamily: 'var(--font-dm-mono)' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#9A8E7E', fontSize: 10, fontFamily: 'var(--font-dm-mono)' }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="boutique" stroke="#B8924A" strokeWidth={1.5} fill="url(#bg)" dot={false} />
              <Area type="monotone" dataKey="online" stroke="#60a5fa" strokeWidth={1.5} fill="url(#og)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
