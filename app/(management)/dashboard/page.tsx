import { prisma } from '@/lib/db'
import { format } from 'date-fns'
import { AlertTriangle, ArrowUpRight, BedDouble, Bell, CheckCircle, Clock, Star, TrendingUp, Users, Wrench } from 'lucide-react'
import Link from 'next/link'
import { cn, PRIORITY_COLORS, STATUS_COLORS, guestName, nightsCount, friendlyDate } from '@/lib/utils'

export const dynamic = 'force-dynamic'
export const metadata = { title: 'Dashboard' }

async function getData() {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return null

  const today = new Date('2026-08-17')
  const todayStart = new Date(today); todayStart.setHours(0, 0, 0, 0)
  const todayEnd = new Date(today); todayEnd.setHours(23, 59, 59, 999)
  const tomorrowStart = new Date(today); tomorrowStart.setDate(tomorrowStart.getDate() + 1); tomorrowStart.setHours(0, 0, 0, 0)
  const tomorrowEnd = new Date(today); tomorrowEnd.setDate(tomorrowEnd.getDate() + 1); tomorrowEnd.setHours(23, 59, 59, 999)

  const [
    allRooms,
    currentStays,
    arrivalsToday,
    departuresToday,
    openRequests,
    pendingHousekeeping,
    openMaintenance,
    recoveryFeedback,
    reviewCandidates,
    directLeads,
    settings,
  ] = await Promise.all([
    prisma.room.findMany({ where: { hotelId: hotel.id }, orderBy: { number: 'asc' } }),
    prisma.stay.findMany({
      where: { hotelId: hotel.id, status: 'CHECKED_IN' },
      include: { guest: true, room: true },
      orderBy: { checkOut: 'asc' },
    }),
    prisma.stay.findMany({
      where: { hotelId: hotel.id, checkIn: { gte: todayStart, lte: todayEnd } },
      include: { guest: true, room: true },
      orderBy: { checkIn: 'asc' },
    }),
    prisma.stay.findMany({
      where: { hotelId: hotel.id, status: 'CHECKED_IN', checkOut: { gte: todayStart, lte: todayEnd } },
      include: { guest: true, room: true },
      orderBy: { checkOut: 'asc' },
    }),
    prisma.serviceRequest.findMany({
      where: { hotelId: hotel.id, status: { notIn: ['COMPLETED', 'CANCELLED'] } },
      include: { room: true, guest: true },
      orderBy: [{ priority: 'desc' }, { createdAt: 'asc' }],
    }),
    prisma.housekeepingTask.findMany({
      where: { hotelId: hotel.id, status: { in: ['PENDING', 'IN_PROGRESS'] } },
      include: { room: true },
      orderBy: [{ priority: 'desc' }, { scheduledFor: 'asc' }],
    }),
    prisma.maintenanceIssue.findMany({
      where: { hotelId: hotel.id, status: { in: ['OPEN', 'IN_PROGRESS'] } },
      include: { room: true },
      orderBy: [{ severity: 'desc' }, { createdAt: 'asc' }],
    }),
    prisma.guestFeedback.findMany({
      where: { hotelId: hotel.id, isRecoveryCase: true, isResolved: false },
      include: { guest: true, stay: { include: { room: true } } },
    }),
    prisma.reviewRequest.findMany({
      where: { hotelId: hotel.id, status: 'CANDIDATE' },
      include: { guest: true, stay: { include: { room: true } } },
    }),
    prisma.directBookingLead.findMany({
      where: { hotelId: hotel.id, status: { in: ['NEW', 'CONTACTED'] } },
      include: { guest: true },
      orderBy: { createdAt: 'desc' },
      take: 3,
    }),
    prisma.hotelSetting.findMany({ where: { hotelId: hotel.id } }),
  ])

  const settingsMap = Object.fromEntries(settings.map(s => [s.key, s.value]))
  const occupiedRooms = allRooms.filter(r => r.status === 'OCCUPIED').length
  const totalActive = allRooms.filter(r => r.status !== 'OUT_OF_SERVICE').length
  const occupancy = Math.round((occupiedRooms / totalActive) * 100)

  return {
    hotel,
    occupancy,
    occupiedRooms,
    totalRooms: allRooms.length,
    currentStays,
    arrivalsToday,
    departuresToday,
    openRequests,
    pendingHousekeeping,
    openMaintenance,
    recoveryFeedback,
    reviewCandidates,
    directLeads,
    settingsMap,
  }
}

export default async function DashboardPage() {
  const data = await getData()
  if (!data) {
    return (
      <div className="flex items-center justify-center h-64 text-[#667085]">
        <div className="text-center">
          <p className="text-lg font-medium mb-2">Database not seeded yet</p>
          <p className="text-sm">Run <code className="bg-gray-100 px-1.5 py-0.5 rounded">npm run setup</code> to initialize A Z Hotel data.</p>
        </div>
      </div>
    )
  }

  const {
    hotel, occupancy, occupiedRooms, totalRooms,
    currentStays, arrivalsToday, departuresToday,
    openRequests, pendingHousekeeping, openMaintenance,
    recoveryFeedback, reviewCandidates, directLeads, settingsMap,
  } = data

  const attentionItems = [
    ...openRequests.filter(r => r.priority === 'HIGH' || r.priority === 'URGENT').map(r => ({
      type: 'request' as const,
      severity: (r.priority === 'URGENT' ? 'critical' : 'high') as 'critical' | 'high' | 'medium',
      title: r.category,
      detail: r.description,
      room: r.room?.number,
      meta: r.status,
      id: r.id,
      status: r.status,
    })),
    ...openMaintenance.filter(m => m.severity === 'CRITICAL' || m.severity === 'HIGH').map(m => ({
      type: 'maintenance' as const,
      severity: m.severity.toLowerCase() as 'critical' | 'high',
      title: m.category.toUpperCase() + ' issue',
      detail: m.description,
      room: m.room?.number,
      meta: m.status,
      id: m.id,
      status: m.status,
    })),
    ...recoveryFeedback.map(f => ({
      type: 'recovery' as const,
      severity: 'high' as const,
      title: 'Guest recovery needed',
      detail: f.comment || 'Negative feedback received',
      room: f.stay?.room?.number,
      meta: 'RECOVERY',
      id: f.id,
      status: 'RECOVERY',
    })),
    ...pendingHousekeeping.filter(h => h.priority === 'HIGH').map(h => ({
      type: 'housekeeping' as const,
      severity: 'medium' as const,
      title: h.type.replace('_', ' '),
      detail: h.notes || 'Housekeeping required',
      room: h.room.number,
      meta: h.status,
      id: h.id,
      status: h.status,
    })),
  ].slice(0, 8)

  const urgentCount = attentionItems.filter(a => a.severity === 'critical' || a.severity === 'high').length
  const summary = [
    arrivalsToday.length > 0 ? `${arrivalsToday.length} arrival${arrivalsToday.length > 1 ? 's' : ''}` : null,
    departuresToday.length > 0 ? `${departuresToday.length} departure${departuresToday.length > 1 ? 's' : ''}` : null,
    urgentCount > 0 ? `${urgentCount} item${urgentCount > 1 ? 's' : ''} need attention` : 'All clear',
  ].filter(Boolean).join(' · ')

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="space-y-6">
      {/* Hero header */}
      <div className="rounded-2xl p-6 text-white relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #121A45 0%, #1E2761 60%, #243070 100%)' }}>
        <div className="absolute inset-0 opacity-5"
          style={{ backgroundImage: 'radial-gradient(circle at 80% -20%, #C9A84C 0%, transparent 50%)' }} />
        <div className="relative">
          <p className="text-[#CADCFC] text-sm mb-1">{greeting}</p>
          <h1 className="font-serif text-3xl font-bold text-white mb-1">{hotel.name}</h1>
          <p className="text-[#C9A84C] text-sm font-medium">{summary}</p>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Occupancy"
          value={`${occupancy}%`}
          sub={`${occupiedRooms} of ${totalRooms} rooms`}
          icon={<BedDouble className="w-5 h-5" />}
          accent="navy"
        />
        <StatCard
          label="Today's Arrivals"
          value={String(arrivalsToday.length)}
          sub={arrivalsToday.map(s => `Room ${s.room.number}`).join(', ') || 'No arrivals'}
          icon={<Users className="w-5 h-5" />}
          accent="gold"
        />
        <StatCard
          label="Open Requests"
          value={String(openRequests.length)}
          sub={openRequests.filter(r => r.priority === 'HIGH').length > 0
            ? `${openRequests.filter(r => r.priority === 'HIGH').length} high priority`
            : 'All normal priority'}
          icon={<Bell className="w-5 h-5" />}
          accent={openRequests.filter(r => r.priority === 'HIGH').length > 0 ? 'amber' : 'green'}
        />
        <StatCard
          label="Review Pipeline"
          value={String(reviewCandidates.length)}
          sub="Candidates ready to request"
          icon={<Star className="w-5 h-5" />}
          accent="green"
        />
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Attention Required */}
        <div className="lg:col-span-2 space-y-4">
          <SectionHeader title="Needs Attention" sub={`${attentionItems.length} active items`} href="/requests">
            {urgentCount > 0 && (
              <span className="badge bg-red-50 text-red-700 border border-red-200">
                <AlertTriangle className="w-3 h-3" /> {urgentCount} urgent
              </span>
            )}
          </SectionHeader>

          {attentionItems.length === 0 ? (
            <div className="data-card p-8 text-center text-[#667085]">
              <CheckCircle className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <p className="font-medium">All clear</p>
              <p className="text-sm">No items currently need attention.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {attentionItems.map((item) => (
                <AttentionRow key={`${item.type}-${item.id}`} item={item} />
              ))}
            </div>
          )}

          {/* Today's timeline */}
          <SectionHeader title="Today at A Z Hotel" sub={format(new Date('2026-08-17'), 'EEEE d MMMM')} href="/guests" />

          <div className="data-card divide-y divide-[#E4E8F1]">
            {arrivalsToday.length === 0 && departuresToday.length === 0 ? (
              <div className="p-6 text-center text-[#667085] text-sm">No arrivals or departures today.</div>
            ) : null}
            {arrivalsToday.map(stay => (
              <div key={stay.id} className="flex items-center gap-4 px-4 py-3.5">
                <div className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-[#182033] text-sm">{guestName(stay.guest)}</div>
                  <div className="text-[#667085] text-xs">{stay.guest.nationality} · {stay.adults} adult{stay.adults > 1 ? 's' : ''} · via {stay.source}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-semibold text-[#1E2761]">Room {stay.room.number}</div>
                  <div className="text-[#667085] text-xs">Check-in {format(new Date(stay.checkIn), 'HH:mm')}</div>
                </div>
                <span className="badge bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px]">ARRIVING</span>
              </div>
            ))}
            {departuresToday.map(stay => (
              <div key={stay.id} className="flex items-center gap-4 px-4 py-3.5">
                <div className="w-2 h-2 rounded-full bg-blue-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-[#182033] text-sm">{guestName(stay.guest)}</div>
                  <div className="text-[#667085] text-xs">{stay.guest.nationality} · {nightsCount(stay.checkIn, stay.checkOut)} nights · {stay.source}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-semibold text-[#1E2761]">Room {stay.room.number}</div>
                  <div className="text-[#667085] text-xs">Checkout by {format(new Date(stay.checkOut), 'HH:mm')}</div>
                </div>
                <span className="badge bg-blue-50 text-blue-700 border border-blue-200 text-[10px]">DEPARTING</span>
              </div>
            ))}
          </div>

          {/* Current guests */}
          <SectionHeader title="Current Guests" sub={`${currentStays.length} in-house`} href="/guests" />
          <div className="data-card divide-y divide-[#E4E8F1]">
            {currentStays.map(stay => {
              const nights = nightsCount(stay.checkIn, new Date('2026-08-17'))
              const remaining = nightsCount(new Date('2026-08-17'), stay.checkOut)
              return (
                <div key={stay.id} className="flex items-center gap-4 px-4 py-3">
                  <div className="w-8 h-8 rounded-full bg-[#1E2761]/10 text-[#1E2761] font-bold text-xs flex items-center justify-center flex-shrink-0">
                    {stay.guest.firstName[0]}{stay.guest.lastName[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-[#182033] text-sm">{guestName(stay.guest)}</div>
                    <div className="text-[#667085] text-xs">{stay.guest.nationality} · Night {nights} of {nights + remaining}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-semibold text-[#1E2761]">Room {stay.room.number}</div>
                    <div className="text-[#667085] text-xs">
                      {remaining === 0 ? '⚠️ Departing today' : remaining === 1 ? 'Departing tomorrow' : `${remaining} nights left`}
                    </div>
                  </div>
                  {stay.guest.isRepeat && (
                    <span className="badge bg-[#C9A84C]/10 text-[#A66E00] text-[10px]">REPEAT</span>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-4">
          {/* AI Brief */}
          <div className="data-card p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-lg bg-[#1E2761] flex items-center justify-center">
                <span className="text-[#C9A84C] text-[10px] font-bold">AI</span>
              </div>
              <span className="text-xs font-semibold text-[#667085] uppercase tracking-wider">Management Brief</span>
            </div>
            <AiBrief
              openRequests={openRequests.length}
              highPriority={openRequests.filter(r => r.priority === 'HIGH').length}
              arrivalsToday={arrivalsToday.length}
              departuresToday={departuresToday.length}
              recoveryFeedback={recoveryFeedback.length}
              reviewCandidates={reviewCandidates.length}
              pendingHousekeeping={pendingHousekeeping.length}
              openMaintenance={openMaintenance.length}
            />
          </div>

          {/* Open Requests Quick View */}
          <div className="data-card">
            <div className="px-4 py-3 border-b border-[#E4E8F1] flex items-center justify-between">
              <span className="font-semibold text-[#182033] text-sm">Open Requests</span>
              <Link href="/requests" className="text-xs text-[#1E2761] hover:underline flex items-center gap-1">
                All <ArrowUpRight className="w-3 h-3" />
              </Link>
            </div>
            <div className="divide-y divide-[#E4E8F1]">
              {openRequests.slice(0, 4).map(req => (
                <div key={req.id} className="px-4 py-3">
                  <div className="flex items-start gap-2 mb-1">
                    <span className={cn('badge text-[10px] flex-shrink-0 mt-0.5', PRIORITY_COLORS[req.priority])}>
                      {req.priority}
                    </span>
                    <span className="text-sm text-[#182033] leading-tight">{req.category}</span>
                  </div>
                  <div className="text-xs text-[#667085] ml-0">
                    Room {req.room?.number} · {friendlyDate(req.createdAt)}
                  </div>
                  <div className="mt-1.5 flex gap-2">
                    <span className={cn('badge text-[10px]', STATUS_COLORS[req.status])}>{req.status.replace('_', ' ')}</span>
                  </div>
                </div>
              ))}
              {openRequests.length === 0 && (
                <div className="px-4 py-6 text-center text-[#667085] text-sm">No open requests</div>
              )}
            </div>
          </div>

          {/* Growth Opportunities */}
          <div className="data-card p-4">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-4 h-4 text-[#C9A84C]" />
              <span className="font-semibold text-[#182033] text-sm">Growth Opportunities</span>
            </div>
            <div className="space-y-3">
              {reviewCandidates.length > 0 && (
                <GrowthItem
                  icon="⭐"
                  title={`${reviewCandidates.length} review ${reviewCandidates.length === 1 ? 'request' : 'requests'} ready`}
                  detail={reviewCandidates.map(r => r.guest.firstName).join(', ')}
                  href="/reputation"
                  cta="Send requests"
                />
              )}
              {recoveryFeedback.length > 0 && (
                <GrowthItem
                  icon="🔧"
                  title={`${recoveryFeedback.length} recovery ${recoveryFeedback.length === 1 ? 'case' : 'cases'} open`}
                  detail="Resolve before checkout to prevent negative reviews"
                  href="/reputation"
                  cta="View cases"
                  urgent
                />
              )}
              {directLeads.length > 0 && (
                <GrowthItem
                  icon="📅"
                  title={`${directLeads.length} direct booking ${directLeads.length === 1 ? 'lead' : 'leads'}`}
                  detail={directLeads.map(l => l.name.split(' ')[0]).join(', ')}
                  href="/guests"
                  cta="Follow up"
                />
              )}
              {openMaintenance.filter(m => m.severity === 'CRITICAL').length > 0 && (
                <GrowthItem
                  icon="⚠️"
                  title="Critical maintenance issue"
                  detail="Room 206 out of service — revenue impact"
                  href="/maintenance"
                  cta="View issue"
                  urgent
                />
              )}
            </div>
          </div>

          {/* Review Scores */}
          <div className="data-card p-4">
            <div className="flex items-center gap-2 mb-3">
              <Star className="w-4 h-4 text-[#C9A84C]" />
              <span className="font-semibold text-[#182033] text-sm">Reputation</span>
            </div>
            <div className="space-y-2">
              <ReviewScore platform="Google" rating={settingsMap.google_rating} count={settingsMap.google_review_count} max={5} />
              <ReviewScore platform="Booking.com" rating={settingsMap.booking_rating} count={settingsMap.booking_review_count} max={10} />
              <ReviewScore platform="TripAdvisor" rating={settingsMap.tripadvisor_rating} count={settingsMap.tripadvisor_review_count} max={5} />
            </div>
            <Link href="/reputation" className="mt-3 flex items-center gap-1 text-xs text-[#1E2761] hover:underline">
              Full reputation view <ArrowUpRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, sub, icon, accent }: {
  label: string; value: string; sub: string
  icon: React.ReactNode; accent: 'navy' | 'gold' | 'green' | 'amber'
}) {
  const accentColors = {
    navy: 'text-[#1E2761] bg-[#1E2761]/5',
    gold: 'text-[#A66E00] bg-[#C9A84C]/10',
    green: 'text-emerald-700 bg-emerald-50',
    amber: 'text-amber-700 bg-amber-50',
  }
  return (
    <div className="stat-card flex items-start gap-4">
      <div className={cn('p-2.5 rounded-xl flex-shrink-0', accentColors[accent])}>
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-xs text-[#667085] mb-0.5">{label}</div>
        <div className="font-serif text-2xl font-bold text-[#182033]">{value}</div>
        <div className="text-xs text-[#667085] truncate mt-0.5">{sub}</div>
      </div>
    </div>
  )
}

function SectionHeader({ title, sub, href, children }: {
  title: string; sub: string; href: string; children?: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h2 className="font-serif text-lg text-[#1E2761]">{title}</h2>
        <p className="text-xs text-[#667085]">{sub}</p>
      </div>
      <div className="flex items-center gap-2">
        {children}
        <Link href={href} className="text-xs text-[#1E2761] hover:underline flex items-center gap-0.5">
          View all <ArrowUpRight className="w-3 h-3" />
        </Link>
      </div>
    </div>
  )
}

type AttentionItem = {
  type: 'request' | 'maintenance' | 'recovery' | 'housekeeping'
  severity: 'critical' | 'high' | 'medium'
  title: string; detail: string; room?: string | null
  meta: string; id: string; status: string
}

function AttentionRow({ item }: { item: AttentionItem }) {
  const severityConfig = {
    critical: { dot: 'bg-red-500', border: 'border-red-200 bg-red-50/50' },
    high: { dot: 'bg-amber-500', border: 'border-amber-200 bg-amber-50/50' },
    medium: { dot: 'bg-blue-400', border: 'border-blue-100 bg-blue-50/50' },
  }
  const cfg = severityConfig[item.severity]
  const icons = {
    request: <Bell className="w-3.5 h-3.5 text-[#667085]" />,
    maintenance: <Wrench className="w-3.5 h-3.5 text-[#667085]" />,
    recovery: <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />,
    housekeeping: <Clock className="w-3.5 h-3.5 text-[#667085]" />,
  }

  return (
    <div className={cn('attention-row', cfg.border)}>
      <div className={cn('w-2 h-2 rounded-full flex-shrink-0 mt-1.5', cfg.dot)} />
      <div className="flex-shrink-0 mt-0.5">{icons[item.type]}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-sm text-[#182033] capitalize">{item.title.toLowerCase()}</span>
          {item.room && (
            <span className="text-xs bg-[#1E2761]/8 text-[#1E2761] px-1.5 py-0.5 rounded font-medium">Room {item.room}</span>
          )}
        </div>
        <p className="text-xs text-[#667085] mt-0.5 leading-relaxed line-clamp-2">{item.detail}</p>
      </div>
      <div className="flex-shrink-0">
        <span className={cn('badge text-[10px]', STATUS_COLORS[item.status] ?? 'bg-gray-100 text-gray-500')}>
          {item.status.replace('_', ' ')}
        </span>
      </div>
    </div>
  )
}

function AiBrief({ openRequests, highPriority, arrivalsToday, departuresToday, recoveryFeedback, reviewCandidates, pendingHousekeeping, openMaintenance }: {
  openRequests: number; highPriority: number; arrivalsToday: number; departuresToday: number
  recoveryFeedback: number; reviewCandidates: number; pendingHousekeeping: number; openMaintenance: number
}) {
  const points: string[] = []
  if (highPriority > 0) points.push(`${highPriority} high-priority request${highPriority > 1 ? 's' : ''} need${highPriority === 1 ? 's' : ''} resolution today — Room 302 AC issue is your most urgent.`)
  if (recoveryFeedback > 0) points.push(`${recoveryFeedback} guest recovery case${recoveryFeedback > 1 ? 's' : ''} open — resolve before checkout to protect your review score.`)
  if (reviewCandidates > 0) points.push(`${reviewCandidates} satisfied guest${reviewCandidates > 1 ? 's' : ''} eligible for a review request — Diego Hernandez leaves tomorrow and is an excellent candidate.`)
  if (arrivalsToday > 0) points.push(`${arrivalsToday} guest${arrivalsToday > 1 ? 's' : ''} arriving today — Blackwoods (Room 401) are returning guests. Personal welcome recommended.`)
  if (pendingHousekeeping > 2) points.push(`${pendingHousekeeping} housekeeping tasks pending. Room 104 priority — previous guest checked out this morning.`)

  if (points.length === 0) {
    points.push('Operations are running smoothly today. Focus on the arriving guests and continue monitoring guest satisfaction.')
  }

  return (
    <div className="space-y-2.5">
      {points.map((point, i) => (
        <div key={i} className="flex gap-2 text-xs text-[#182033] leading-relaxed">
          <span className="text-[#C9A84C] font-bold flex-shrink-0">{i + 1}.</span>
          <span>{point}</span>
        </div>
      ))}
    </div>
  )
}

function GrowthItem({ icon, title, detail, href, cta, urgent }: {
  icon: string; title: string; detail: string; href: string; cta: string; urgent?: boolean
}) {
  return (
    <div className={cn('rounded-xl p-3 border', urgent ? 'bg-amber-50 border-amber-200' : 'bg-[#F5F7FB] border-[#E4E8F1]')}>
      <div className="flex items-start gap-2">
        <span className="text-base flex-shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-[#182033]">{title}</div>
          <div className="text-xs text-[#667085] mt-0.5">{detail}</div>
          <Link href={href} className="mt-1.5 inline-flex text-[10px] font-semibold text-[#1E2761] hover:underline">
            {cta} →
          </Link>
        </div>
      </div>
    </div>
  )
}

function ReviewScore({ platform, rating, count, max }: {
  platform: string; rating: string; count: string; max: number
}) {
  const r = parseFloat(rating || '0')
  const pct = (r / max) * 100
  const color = pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-3">
      <div className="w-20 text-xs text-[#667085] flex-shrink-0">{platform}</div>
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
      </div>
      <div className="text-xs font-semibold text-[#182033] w-8 text-right">{rating}</div>
      <div className="text-[10px] text-[#667085] w-14 text-right">{count} reviews</div>
    </div>
  )
}

// Placeholder — interactivity handled client-side in requests page
function RequestUpdateButton({ id, currentStatus }: { id: string; currentStatus: string }) {
  return null
}
