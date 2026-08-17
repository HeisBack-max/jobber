import { prisma } from '@/lib/db'
import { cn, guestName, friendlyDate } from '@/lib/utils'
import { Star, AlertTriangle, CheckCircle } from 'lucide-react'

export const dynamic = 'force-dynamic'
export const metadata = { title: 'Reputation' }

async function getData() {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return null

  const [feedback, reviewCandidates, settings] = await Promise.all([
    prisma.guestFeedback.findMany({
      where: { hotelId: hotel.id },
      include: {
        guest: true,
        stay: { include: { room: true } },
      },
      orderBy: { createdAt: 'desc' },
    }),
    prisma.reviewRequest.findMany({
      where: { hotelId: hotel.id },
      include: {
        guest: true,
        stay: { include: { room: true } },
      },
      orderBy: { createdAt: 'desc' },
    }),
    prisma.hotelSetting.findMany({ where: { hotelId: hotel.id } }),
  ])

  const settingsMap = Object.fromEntries(settings.map(s => [s.key, s.value]))
  return { hotel, feedback, reviewCandidates, settingsMap }
}

export default async function ReputationPage() {
  const data = await getData()
  if (!data) return null
  const { feedback, reviewCandidates, settingsMap } = data

  const recoveryFeedback = feedback.filter(f => f.isRecoveryCase && !f.isResolved)
  const positiveFeedback = feedback.filter(f => f.sentiment === 'POSITIVE')
  const negativeFeedback = feedback.filter(f => f.sentiment === 'NEGATIVE')
  const candidates = reviewCandidates.filter(r => r.status === 'CANDIDATE')

  const avgRating = feedback.filter(f => f.rating).reduce((acc, f, _, arr) =>
    acc + (f.rating || 0) / arr.length, 0
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="section-title">Reputation</h1>
        <p className="section-subtitle">Guest feedback, review pipeline, and recovery cases</p>
      </div>

      {/* Platform scores */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { platform: 'Google', rating: settingsMap.google_rating, count: settingsMap.google_review_count, max: 5, color: 'text-red-500' },
          { platform: 'Booking.com', rating: settingsMap.booking_rating, count: settingsMap.booking_review_count, max: 10, color: 'text-[#1E2761]' },
          { platform: 'TripAdvisor', rating: settingsMap.tripadvisor_rating, count: settingsMap.tripadvisor_review_count, max: 5, color: 'text-emerald-600' },
        ].map(p => (
          <div key={p.platform} className="stat-card text-center">
            <div className={cn('font-serif text-4xl font-bold', p.color)}>{p.rating}</div>
            <div className="text-xs text-[#667085] mt-1">/ {p.max} · {p.count} reviews</div>
            <div className="font-medium text-sm text-[#182033] mt-2">{p.platform}</div>
            <div className="mt-2 flex justify-center">
              {[...Array(5)].map((_, i) => (
                <Star key={i}
                  className={cn('w-3 h-3', i < Math.round(parseFloat(p.rating) / (p.max / 5)) ? 'text-[#C9A84C]' : 'text-gray-200')}
                  fill={i < Math.round(parseFloat(p.rating) / (p.max / 5)) ? 'currentColor' : 'none'}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Recovery cases — urgent */}
      {recoveryFeedback.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            <h2 className="font-serif text-lg text-[#1E2761]">Recovery Cases</h2>
            <span className="badge bg-red-50 text-red-700 border border-red-200">{recoveryFeedback.length} open</span>
          </div>
          <div className="space-y-3">
            {recoveryFeedback.map(f => (
              <div key={f.id} className="rounded-xl border border-red-200 bg-red-50 p-4">
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-[#182033]">{guestName(f.guest!)}</span>
                      {f.stay?.room && (
                        <span className="badge bg-white border border-red-200 text-red-700 text-[10px]">Room {f.stay.room.number}</span>
                      )}
                    </div>
                    <div className="text-xs text-[#667085] mt-0.5">{friendlyDate(f.createdAt)}</div>
                  </div>
                  <div className="flex gap-1">
                    {f.rating && [...Array(5)].map((_, i) => (
                      <Star key={i} className={cn('w-3.5 h-3.5', i < f.rating! ? 'text-[#C9A84C]' : 'text-gray-300')} fill={i < f.rating! ? 'currentColor' : 'none'} />
                    ))}
                  </div>
                </div>
                <p className="text-sm text-[#182033] italic mb-3">"{f.comment}"</p>
                {f.recoveryNotes && (
                  <div className="text-xs bg-white/60 rounded-lg p-2 mb-3 text-[#667085]">
                    📋 Staff note: {f.recoveryNotes}
                  </div>
                )}
                <div className="flex gap-2">
                  <button className="text-xs bg-red-700 text-white px-3 py-1.5 rounded-lg hover:bg-red-800">Resolve & Compensate</button>
                  <button className="text-xs border border-red-200 text-red-700 px-3 py-1.5 rounded-lg hover:bg-red-100">Add Note</button>
                </div>
                <div className="mt-2 text-[10px] text-red-600 font-medium">⚠️ Do not send review request until resolved</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Review candidates */}
      {candidates.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Star className="w-4 h-4 text-[#C9A84C]" />
            <h2 className="font-serif text-lg text-[#1E2761]">Review Request Candidates</h2>
            <span className="badge bg-[#C9A84C]/10 text-[#A66E00]">{candidates.length} ready</span>
          </div>
          <div className="data-card divide-y divide-[#E4E8F1]">
            {candidates.map(r => {
              const positiveFb = feedback.find(f => f.guestId === r.guestId && f.sentiment === 'POSITIVE')
              return (
                <div key={r.id} className="px-4 py-4 flex items-start gap-4">
                  <div className="w-9 h-9 rounded-full bg-[#C9A84C]/15 text-[#A66E00] font-bold text-sm flex items-center justify-center flex-shrink-0">
                    {r.guest.firstName[0]}{r.guest.lastName[0]}
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-[#182033]">{guestName(r.guest)}</div>
                    {r.stay?.room && (
                      <div className="text-xs text-[#667085]">Room {r.stay.room.number} · via {r.platform}</div>
                    )}
                    {positiveFb?.comment && (
                      <div className="text-xs text-[#667085] mt-1 italic">"{positiveFb.comment.slice(0, 100)}..."</div>
                    )}
                    <div className="text-xs text-emerald-600 mt-1">✓ Positive stay confirmed · No unresolved issues</div>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <button className="text-xs bg-[#C9A84C] text-[#121A45] px-3 py-1.5 rounded-lg hover:bg-[#E8C96A] font-semibold">
                      Send Request
                    </button>
                    <button className="text-xs border border-[#E4E8F1] text-[#667085] px-3 py-1.5 rounded-lg hover:bg-gray-50">Hold</button>
                  </div>
                </div>
              )
            })}
          </div>
          <div className="mt-2 text-xs text-[#667085] px-1">
            Review requests are sent to satisfied guests only. The system blocks requests when a recovery case is open.
          </div>
        </div>
      )}

      {/* All feedback */}
      <div>
        <h2 className="font-serif text-lg text-[#1E2761] mb-3">Guest Feedback</h2>
        <div className="space-y-3">
          {feedback.map(f => (
            <div key={f.id} className={cn(
              'rounded-xl border p-4',
              f.sentiment === 'POSITIVE' ? 'bg-emerald-50 border-emerald-200' :
              f.sentiment === 'NEGATIVE' ? 'bg-red-50 border-red-200' : 'bg-gray-50 border-gray-200'
            )}>
              <div className="flex items-start justify-between gap-4 mb-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className={cn('text-sm font-semibold',
                      f.sentiment === 'POSITIVE' ? 'text-emerald-800' :
                      f.sentiment === 'NEGATIVE' ? 'text-red-800' : 'text-[#667085]'
                    )}>
                      {guestName(f.guest!)}
                    </span>
                    {f.stay?.room && (
                      <span className="badge bg-white border border-gray-200 text-[#667085] text-[10px]">Room {f.stay.room.number}</span>
                    )}
                    {f.isRecoveryCase && (
                      <span className="badge bg-red-100 text-red-700 text-[10px]">RECOVERY</span>
                    )}
                  </div>
                  <div className="text-xs text-[#667085] mt-0.5">{f.category} · {friendlyDate(f.createdAt)}</div>
                </div>
                <div className="flex items-center gap-1">
                  {f.rating && [...Array(5)].map((_, i) => (
                    <Star key={i}
                      className={cn('w-3.5 h-3.5', i < f.rating! ? 'text-[#C9A84C]' : 'text-gray-200')}
                      fill={i < f.rating! ? 'currentColor' : 'none'}
                    />
                  ))}
                  <span className="text-xs font-semibold text-[#182033] ml-1">{f.rating}/5</span>
                </div>
              </div>
              {f.comment && (
                <p className="text-sm text-[#182033] italic">"{f.comment}"</p>
              )}
              {f.isResolved && (
                <div className="flex items-center gap-1 mt-2 text-xs text-emerald-700">
                  <CheckCircle className="w-3.5 h-3.5" /> Resolved
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* AI Response suggestion */}
      <div className="data-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-6 h-6 rounded-lg bg-[#1E2761] flex items-center justify-center">
            <span className="text-[#C9A84C] text-[10px] font-bold">AI</span>
          </div>
          <span className="font-semibold text-sm text-[#182033]">Suggested Response — Negative Feedback (Emma Wilson)</span>
        </div>
        <div className="bg-[#F5F7FB] rounded-xl p-4 text-sm text-[#182033] italic leading-relaxed">
          "Dear Emma, thank you for taking the time to share your experience. We sincerely apologise that the air conditioning in your room did not meet the standard you deserved. Our maintenance team is actively working to resolve the issue and we have prioritised your comfort. We would like to offer [compensation/upgrade] as a gesture of goodwill. Please do not hesitate to speak with our team directly — we are committed to making the rest of your stay as comfortable as possible. Warmly, The A Z Hotel Team."
        </div>
        <div className="flex gap-2 mt-3">
          <button className="text-xs bg-[#1E2761] text-white px-3 py-1.5 rounded-lg">Use This Response</button>
          <button className="text-xs border border-[#E4E8F1] text-[#667085] px-3 py-1.5 rounded-lg">Edit</button>
        </div>
      </div>
    </div>
  )
}
