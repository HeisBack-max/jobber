import { prisma } from '@/lib/db'
import { cn } from '@/lib/utils'
import { TrendingUp, Star, MessageSquare, Wrench, Users, BedDouble } from 'lucide-react'

export const dynamic = 'force-dynamic'
export const metadata = { title: 'Analytics' }

async function getData() {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return null

  const [rooms, stays, feedback, requests, maintenance, settings] = await Promise.all([
    prisma.room.findMany({ where: { hotelId: hotel.id } }),
    prisma.stay.findMany({ where: { hotelId: hotel.id }, include: { room: true, guest: true } }),
    prisma.guestFeedback.findMany({ where: { hotelId: hotel.id } }),
    prisma.serviceRequest.findMany({ where: { hotelId: hotel.id } }),
    prisma.maintenanceIssue.findMany({ where: { hotelId: hotel.id } }),
    prisma.hotelSetting.findMany({ where: { hotelId: hotel.id } }),
  ])

  const settingsMap = Object.fromEntries(settings.map(s => [s.key, s.value]))
  return { hotel, rooms, stays, feedback, requests, maintenance, settingsMap }
}

export default async function AnalyticsPage() {
  const data = await getData()
  if (!data) return null
  const { rooms, stays, feedback, requests, maintenance, settingsMap } = data

  const totalRooms = rooms.length
  const occupiedRooms = rooms.filter(r => r.status === 'OCCUPIED').length
  const occupancyPct = Math.round((occupiedRooms / totalRooms) * 100)
  const outOfService = rooms.filter(r => r.status === 'OUT_OF_SERVICE').length

  const avgRating = feedback.filter(f => f.rating).length > 0
    ? (feedback.filter(f => f.rating).reduce((acc, f) => acc + (f.rating || 0), 0) / feedback.filter(f => f.rating).length).toFixed(1)
    : '–'

  const positivePct = feedback.length > 0
    ? Math.round((feedback.filter(f => f.sentiment === 'POSITIVE').length / feedback.length) * 100)
    : 0

  const resolvedRequests = requests.filter(r => r.status === 'COMPLETED').length
  const requestResolutionPct = requests.length > 0 ? Math.round((resolvedRequests / requests.length) * 100) : 0

  const resolvedMaintenance = maintenance.filter(m => m.status === 'RESOLVED').length

  const categoryBreakdown: Record<string, number> = {}
  requests.forEach(r => {
    categoryBreakdown[r.category] = (categoryBreakdown[r.category] || 0) + 1
  })

  const sourceBreakdown: Record<string, number> = {}
  stays.forEach(s => {
    if (s.source) sourceBreakdown[s.source] = (sourceBreakdown[s.source] || 0) + 1
  })

  const sentimentCounts = {
    POSITIVE: feedback.filter(f => f.sentiment === 'POSITIVE').length,
    NEUTRAL: feedback.filter(f => f.sentiment === 'NEUTRAL').length,
    NEGATIVE: feedback.filter(f => f.sentiment === 'NEGATIVE').length,
  }

  const roomTypeRevenue: Record<string, { rooms: number; rate: number }> = {}
  rooms.forEach(r => {
    if (!roomTypeRevenue[r.type]) roomTypeRevenue[r.type] = { rooms: 0, rate: r.pricePerNight }
    roomTypeRevenue[r.type].rooms++
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="section-title">Analytics</h1>
        <p className="section-subtitle">Performance overview · A Z Hotel Phnom Penh</p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon: BedDouble, label: 'Occupancy', value: `${occupancyPct}%`, sub: `${occupiedRooms}/${totalRooms} rooms`, color: 'text-[#1E2761]' },
          { icon: Star, label: 'Avg Rating', value: avgRating, sub: `${feedback.filter(f=>f.rating).length} reviews`, color: 'text-[#C9A84C]' },
          { icon: MessageSquare, label: 'Positive Feedback', value: `${positivePct}%`, sub: `${sentimentCounts.POSITIVE} of ${feedback.length} responses`, color: 'text-emerald-600' },
          { icon: Wrench, label: 'Request Resolution', value: `${requestResolutionPct}%`, sub: `${resolvedRequests}/${requests.length} completed`, color: 'text-blue-600' },
        ].map(kpi => (
          <div key={kpi.label} className="stat-card">
            <div className="flex items-center gap-2 mb-2">
              <kpi.icon className={cn('w-4 h-4', kpi.color)} />
              <span className="text-xs text-[#667085] font-medium">{kpi.label}</span>
            </div>
            <div className={cn('font-serif text-3xl font-bold', kpi.color)}>{kpi.value}</div>
            <div className="text-xs text-[#667085] mt-1">{kpi.sub}</div>
          </div>
        ))}
      </div>

      {/* Platform scores */}
      <div className="data-card p-5">
        <h2 className="font-serif text-lg text-[#1E2761] mb-4">Platform Reputation</h2>
        <div className="grid grid-cols-3 gap-6">
          {[
            { platform: 'Google', rating: settingsMap.google_rating || '4.2', max: 5, count: settingsMap.google_review_count || '184', color: 'bg-red-500' },
            { platform: 'Booking.com', rating: settingsMap.booking_rating || '8.1', max: 10, count: settingsMap.booking_review_count || '312', color: 'bg-[#1E2761]' },
            { platform: 'TripAdvisor', rating: settingsMap.tripadvisor_rating || '4.0', max: 5, count: settingsMap.tripadvisor_review_count || '97', color: 'bg-emerald-600' },
          ].map(p => {
            const pct = (parseFloat(p.rating) / p.max) * 100
            return (
              <div key={p.platform}>
                <div className="flex items-end justify-between mb-1">
                  <span className="text-sm font-semibold text-[#182033]">{p.platform}</span>
                  <span className="font-serif text-2xl font-bold text-[#1E2761]">{p.rating}<span className="text-sm text-[#667085] font-normal">/{p.max}</span></span>
                </div>
                <div className="h-2 bg-[#E4E8F1] rounded-full overflow-hidden">
                  <div className={cn('h-full rounded-full', p.color)} style={{ width: `${pct}%` }} />
                </div>
                <div className="text-xs text-[#667085] mt-1">{p.count} reviews</div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Guest sentiment */}
        <div className="data-card p-5">
          <h2 className="font-serif text-lg text-[#1E2761] mb-4">Guest Sentiment</h2>
          <div className="space-y-3">
            {[
              { label: 'Positive', count: sentimentCounts.POSITIVE, color: 'bg-emerald-500', textColor: 'text-emerald-700' },
              { label: 'Neutral', count: sentimentCounts.NEUTRAL, color: 'bg-gray-400', textColor: 'text-gray-600' },
              { label: 'Negative', count: sentimentCounts.NEGATIVE, color: 'bg-red-500', textColor: 'text-red-700' },
            ].map(s => {
              const pct = feedback.length > 0 ? Math.round((s.count / feedback.length) * 100) : 0
              return (
                <div key={s.label}>
                  <div className="flex items-center justify-between mb-1">
                    <span className={cn('text-sm font-medium', s.textColor)}>{s.label}</span>
                    <span className="text-sm font-semibold text-[#182033]">{s.count} <span className="text-[#667085] font-normal text-xs">({pct}%)</span></span>
                  </div>
                  <div className="h-2 bg-[#E4E8F1] rounded-full overflow-hidden">
                    <div className={cn('h-full rounded-full', s.color)} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            })}
          </div>
          <div className="mt-4 pt-4 border-t border-[#E4E8F1] text-xs text-[#667085]">
            Based on {feedback.length} guest feedback responses
          </div>
        </div>

        {/* Booking sources */}
        <div className="data-card p-5">
          <h2 className="font-serif text-lg text-[#1E2761] mb-4">Booking Sources</h2>
          <div className="space-y-3">
            {Object.entries(sourceBreakdown).sort((a, b) => b[1] - a[1]).map(([source, count]) => {
              const pct = stays.length > 0 ? Math.round((count / stays.length) * 100) : 0
              return (
                <div key={source}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-[#182033] capitalize">{source.replace('_', ' ').toLowerCase()}</span>
                    <span className="text-sm font-semibold text-[#182033]">{count} <span className="text-[#667085] font-normal text-xs">({pct}%)</span></span>
                  </div>
                  <div className="h-2 bg-[#E4E8F1] rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-[#1E2761]" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            })}
          </div>
          <div className="mt-4 pt-4 border-t border-[#E4E8F1] text-xs text-[#667085]">
            {stays.length} total bookings tracked
          </div>
        </div>

        {/* Service requests by category */}
        <div className="data-card p-5">
          <h2 className="font-serif text-lg text-[#1E2761] mb-4">Service Request Categories</h2>
          <div className="space-y-2">
            {Object.entries(categoryBreakdown).sort((a, b) => b[1] - a[1]).map(([cat, count]) => {
              const pct = requests.length > 0 ? Math.round((count / requests.length) * 100) : 0
              return (
                <div key={cat} className="flex items-center gap-3">
                  <span className="text-xs text-[#667085] w-24 capitalize">{cat.replace('_', ' ').toLowerCase()}</span>
                  <div className="flex-1 h-2 bg-[#E4E8F1] rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-[#C9A84C]" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-xs font-semibold text-[#182033] w-8 text-right">{count}</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Room type breakdown */}
        <div className="data-card p-5">
          <h2 className="font-serif text-lg text-[#1E2761] mb-4">Room Type Inventory</h2>
          <div className="space-y-3">
            {Object.entries(roomTypeRevenue).map(([type, info]) => (
              <div key={type} className="flex items-center justify-between py-2 border-b border-[#E4E8F1] last:border-0">
                <div>
                  <div className="font-medium text-sm text-[#182033]">{type}</div>
                  <div className="text-xs text-[#667085]">{info.rooms} rooms</div>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-[#1E2761]">${info.rate}/night</div>
                  <div className="text-xs text-[#667085]">rack rate</div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-3 border-t border-[#E4E8F1]">
            <div className="flex justify-between text-sm">
              <span className="text-[#667085]">Out of service</span>
              <span className="font-semibold text-red-600">{outOfService} rooms</span>
            </div>
          </div>
        </div>
      </div>

      {/* Maintenance summary */}
      <div className="data-card p-5">
        <h2 className="font-serif text-lg text-[#1E2761] mb-4">Maintenance Overview</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Issues', value: maintenance.length, color: 'text-[#182033]' },
            { label: 'Critical Open', value: maintenance.filter(m => m.severity === 'CRITICAL' && m.status !== 'RESOLVED').length, color: 'text-red-600' },
            { label: 'In Progress', value: maintenance.filter(m => m.status === 'IN_PROGRESS').length, color: 'text-blue-600' },
            { label: 'Resolved', value: resolvedMaintenance, color: 'text-emerald-600' },
          ].map(s => (
            <div key={s.label} className="text-center p-3 bg-[#F5F7FB] rounded-xl">
              <div className={cn('font-serif text-3xl font-bold', s.color)}>{s.value}</div>
              <div className="text-xs text-[#667085] mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="text-xs text-[#667085] text-center">
        Analytics based on live hotel data · Refreshed on each page load
      </div>
    </div>
  )
}
