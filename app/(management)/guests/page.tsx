import { prisma } from '@/lib/db'
import { format } from 'date-fns'
import { cn, guestName, nightsCount } from '@/lib/utils'
import { Users, Star, RepeatIcon } from 'lucide-react'

export const dynamic = 'force-dynamic'
export const metadata = { title: 'Guests' }

async function getData() {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return null

  const stays = await prisma.stay.findMany({
    where: { hotelId: hotel.id, status: 'CHECKED_IN' },
    include: {
      guest: {
        include: {
          feedback: { orderBy: { createdAt: 'desc' }, take: 1 },
        },
      },
      room: true,
      serviceRequests: { where: { status: { notIn: ['COMPLETED', 'CANCELLED'] } } },
    },
    orderBy: { checkOut: 'asc' },
  })

  const directLeads = await prisma.directBookingLead.findMany({
    where: { hotelId: hotel.id, status: { in: ['NEW', 'CONTACTED'] } },
    include: { guest: true },
    orderBy: { createdAt: 'desc' },
  })

  return { hotel, stays, directLeads }
}

const FLAG: Record<string, string> = {
  Chinese: '🇨🇳', British: '🇬🇧', Indian: '🇮🇳', American: '🇺🇸',
  Japanese: '🇯🇵', Mexican: '🇲🇽', Australian: '🇦🇺', Vietnamese: '🇻🇳', French: '🇫🇷',
}

export default async function GuestsPage() {
  const data = await getData()
  if (!data) return null
  const { stays, directLeads } = data

  const departingToday = stays.filter(s => {
    const co = new Date(s.checkOut)
    return co.toDateString() === new Date('2026-08-17').toDateString()
  })
  const departingTomorrow = stays.filter(s => {
    const co = new Date(s.checkOut)
    const tomorrow = new Date('2026-08-18')
    return co.toDateString() === tomorrow.toDateString()
  })

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="section-title">Guests</h1>
          <p className="section-subtitle">{stays.length} guests currently in-house</p>
        </div>
        <div className="flex gap-2 text-xs">
          {departingToday.length > 0 && (
            <span className="badge bg-blue-50 text-blue-700 border border-blue-200">
              {departingToday.length} departing today
            </span>
          )}
          {departingTomorrow.length > 0 && (
            <span className="badge bg-amber-50 text-amber-700 border border-amber-200">
              {departingTomorrow.length} departing tomorrow
            </span>
          )}
        </div>
      </div>

      {/* Guest grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {stays.map(stay => {
          const today = new Date('2026-08-17')
          const nightIn = nightsCount(stay.checkIn, today)
          const nightsLeft = nightsCount(today, stay.checkOut)
          const lastFeedback = stay.guest.feedback[0]
          const flag = FLAG[stay.guest.nationality || ''] || '🌍'
          const departingStatus =
            nightsLeft === 0 ? 'today' : nightsLeft === 1 ? 'tomorrow' : null

          return (
            <div key={stay.id} className={cn(
              'data-card p-4',
              departingStatus === 'today' && 'border-l-4 border-l-blue-500',
              stay.guest.isRepeat && 'border-l-4 border-l-[#C9A84C]',
              lastFeedback?.isRecoveryCase && !lastFeedback.isResolved && 'border-l-4 border-l-red-500',
            )}>
              <div className="flex items-start gap-3 mb-3">
                <div className="w-10 h-10 rounded-full bg-[#1E2761]/10 text-[#1E2761] font-bold flex items-center justify-center text-sm flex-shrink-0">
                  {stay.guest.firstName[0]}{stay.guest.lastName[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-semibold text-[#182033]">{guestName(stay.guest)}</span>
                    {stay.guest.isRepeat && (
                      <span title="Returning guest">
                        <Star className="w-3.5 h-3.5 text-[#C9A84C]" fill="currentColor" />
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-[#667085]">{flag} {stay.guest.nationality} · Room {stay.room.number} · {stay.room.type}</div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="font-bold text-[#1E2761] text-sm">Room {stay.room.number}</div>
                  <div className={cn('text-[10px] font-semibold mt-0.5',
                    departingStatus === 'today' ? 'text-blue-600' :
                    departingStatus === 'tomorrow' ? 'text-amber-600' : 'text-[#667085]'
                  )}>
                    {departingStatus === 'today' ? 'DEPARTING TODAY' :
                     departingStatus === 'tomorrow' ? 'DEP. TOMORROW' :
                     `${nightsLeft} nights left`}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                <div className="bg-[#F5F7FB] rounded-lg p-2">
                  <div className="text-[#667085]">Check-in</div>
                  <div className="font-medium text-[#182033]">{format(new Date(stay.checkIn), 'dd MMM')}</div>
                  <div className="text-[#667085]">Night {nightIn}</div>
                </div>
                <div className="bg-[#F5F7FB] rounded-lg p-2">
                  <div className="text-[#667085]">Check-out</div>
                  <div className="font-medium text-[#182033]">{format(new Date(stay.checkOut), 'dd MMM, HH:mm')}</div>
                  <div className="text-[#667085]">via {stay.source}</div>
                </div>
              </div>

              {stay.guest.notes && (
                <div className="text-xs text-[#667085] bg-[#FFF8E7] border border-[#C9A84C]/20 rounded-lg p-2 mb-2 leading-relaxed">
                  {stay.guest.notes}
                </div>
              )}

              {lastFeedback?.isRecoveryCase && !lastFeedback.isResolved && (
                <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg p-2">
                  ⚠️ Recovery case — guest unhappy. Action required.
                </div>
              )}

              {stay.serviceRequests.length > 0 && (
                <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-2">
                  🔔 {stay.serviceRequests.length} open request{stay.serviceRequests.length > 1 ? 's' : ''}
                </div>
              )}

              <div className="mt-3 flex gap-2">
                <button className="text-xs bg-[#1E2761] text-white px-3 py-1.5 rounded-lg hover:bg-[#243070] transition-colors">
                  View Profile
                </button>
                {departingStatus && (
                  <button className="text-xs bg-[#F5F7FB] border border-[#E4E8F1] text-[#182033] px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors">
                    Checkout Actions
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Direct booking leads */}
      {directLeads.length > 0 && (
        <div>
          <h2 className="font-serif text-xl text-[#1E2761] mb-1">Direct Booking Leads</h2>
          <p className="text-sm text-[#667085] mb-4">Return guests and direct inquiries — your owned relationships</p>
          <div className="data-card divide-y divide-[#E4E8F1]">
            {directLeads.map(lead => (
              <div key={lead.id} className="px-4 py-4 flex items-start gap-4">
                <div className="w-9 h-9 rounded-full bg-[#C9A84C]/15 text-[#A66E00] font-bold text-sm flex items-center justify-center flex-shrink-0">
                  {lead.name.split(' ')[0][0]}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-[#182033]">{lead.name}</span>
                    <span className="badge bg-[#C9A84C]/10 text-[#A66E00] text-[10px]">{lead.source.toUpperCase()}</span>
                  </div>
                  {lead.checkIn && lead.checkOut && (
                    <div className="text-xs text-[#667085] mt-0.5">
                      {format(new Date(lead.checkIn), 'dd MMM')} – {format(new Date(lead.checkOut), 'dd MMM yyyy')} · {lead.adults} adult{lead.adults !== 1 ? 's' : ''}
                    </div>
                  )}
                  {lead.message && (
                    <div className="text-xs text-[#667085] mt-1 leading-relaxed italic">"{lead.message}"</div>
                  )}
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  <button className="text-xs bg-[#1E2761] text-white px-3 py-1.5 rounded-lg hover:bg-[#243070]">Reply</button>
                  <button className="text-xs border border-[#E4E8F1] text-[#667085] px-3 py-1.5 rounded-lg hover:bg-gray-50">Quote</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
