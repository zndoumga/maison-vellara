'use client'
import { useEffect, useState, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import { STORE_NAMES, VIP_BADGE } from '@/lib/constants'
import PageHeader from '@/components/PageHeader'

const PAGE_SIZE = 50

interface Client {
  client_id: string; first_name: string; last_name: string; email: string | null
  phone: string | null; nationality: string; country_of_residence: string
  vip_tier: string; assigned_store_id: string; acquisition_channel: string
  created_at: string
}

export default function ClientsPage() {
  const [rows, setRows] = useState<Client[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    // distinct latest record per client via ordering; CRM is a delta feed
    let q = supabase.schema('crm').from('clients')
      .select('client_id,first_name,last_name,email,phone,nationality,country_of_residence,vip_tier,assigned_store_id,acquisition_channel,created_at', { count: 'exact' })
      .order('created_at', { ascending: false })
      .range(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE - 1)
    if (search) q = q.or(`first_name.ilike.%${search}%,last_name.ilike.%${search}%,email.ilike.%${search}%`)
    const { data, count } = await q
    setRows((data as Client[]) ?? [])
    setTotal(count ?? 0)
    setLoading(false)
  }, [page, search])

  useEffect(() => { load() }, [load])
  useEffect(() => { const t = setTimeout(() => setPage(0), 300); return () => clearTimeout(t) }, [search])

  const pages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="p-6 md:p-8 max-w-[1400px] mx-auto">
      <PageHeader title="Clients" subtitle="CRM — Source 1 · Supabase Postgres (delta feed)" />

      <div className="flex flex-wrap gap-3 mb-4 items-center">
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search name or email…"
          className="bg-white border border-paper-border rounded-sm px-3 py-1.5 text-xs font-mono text-ink w-64 placeholder:text-ink-faint" />
        <span className="text-xs text-ink-faint font-mono ml-auto">{total.toLocaleString()} client records</span>
      </div>

      <div className="card overflow-x-auto">
        <table>
          <thead><tr>
            <th>Client ID</th><th>Name</th><th>Email</th><th>Phone</th><th>Nationality</th>
            <th>Residence</th><th>Tier</th><th>Home Store</th><th>Channel</th><th>Registered</th>
          </tr></thead>
          <tbody>
            {loading ? (
              [...Array(10)].map((_, i) => <tr key={i}><td colSpan={10}><div className="h-5 bg-paper rounded animate-pulse" /></td></tr>)
            ) : rows.map(c => (
              <tr key={c.client_id + c.created_at}>
                <td className="text-ink-faint">{c.client_id}</td>
                <td className="text-ink whitespace-nowrap">{c.first_name} {c.last_name}</td>
                <td className="text-ink-muted">{c.email ?? <span className="italic text-ink-faint/60">none</span>}</td>
                <td className="text-ink-faint">{c.phone ?? '—'}</td>
                <td className="text-ink-muted">{c.nationality}</td>
                <td className="text-ink-faint">{c.country_of_residence}</td>
                <td><span className={`text-[10px] px-1.5 py-0.5 rounded border capitalize ${VIP_BADGE[c.vip_tier] ?? VIP_BADGE.standard}`}>{c.vip_tier}</span></td>
                <td className="text-ink-faint whitespace-nowrap">{STORE_NAMES[c.assigned_store_id] ?? c.assigned_store_id}</td>
                <td className="text-ink-faint">{c.acquisition_channel}</td>
                <td className="text-ink-faint whitespace-nowrap">{c.created_at?.slice(0,10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-4 text-xs font-mono text-ink-muted">
        <button disabled={page === 0} onClick={() => setPage(p => p - 1)}
          className="px-3 py-1.5 border border-paper-border rounded-sm disabled:opacity-30 hover:bg-paper-hover">← Prev</button>
        <span>Page {page + 1} of {pages || 1}</span>
        <button disabled={page >= pages - 1} onClick={() => setPage(p => p + 1)}
          className="px-3 py-1.5 border border-paper-border rounded-sm disabled:opacity-30 hover:bg-paper-hover">Next →</button>
      </div>
      <p className="text-[10px] text-ink-faint mt-3 font-mono">
        Note: CRM is a delta feed — a client may appear multiple times as their record is updated. Identity resolution is handled downstream in dbt.
      </p>
    </div>
  )
}
