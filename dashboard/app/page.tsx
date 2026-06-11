import PageHeader from '@/components/PageHeader'
import KpiRow from '@/components/KpiRow'
import LiveFeed from '@/components/LiveFeed'
import SalesChart from '@/components/SalesChart'
import InventoryAlerts from '@/components/InventoryAlerts'
import WholesaleCards from '@/components/WholesaleCards'

export default function Overview() {
  return (
    <div className="p-6 md:p-8 max-w-[1400px] mx-auto">
      <PageHeader title="Overview" subtitle="Omnichannel performance across boutiques, online and wholesale" />
      <KpiRow />
      <section className="grid grid-cols-1 xl:grid-cols-2 gap-3 mb-3">
        <LiveFeed />
        <SalesChart />
      </section>
      <section className="grid grid-cols-1 xl:grid-cols-2 gap-3">
        <InventoryAlerts />
        <WholesaleCards />
      </section>
    </div>
  )
}
