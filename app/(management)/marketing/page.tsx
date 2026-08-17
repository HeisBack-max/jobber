import { prisma } from '@/lib/db'
import { cn, friendlyDate } from '@/lib/utils'

export const dynamic = 'force-dynamic'
export const metadata = { title: 'Marketing' }

async function getData() {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return null

  const [content, feedback, leads, settings] = await Promise.all([
    prisma.marketingContent.findMany({
      where: { hotelId: hotel.id },
      orderBy: { createdAt: 'desc' },
    }),
    prisma.guestFeedback.findMany({
      where: { hotelId: hotel.id, sentiment: 'POSITIVE' },
      include: { guest: true },
      take: 5,
    }),
    prisma.directBookingLead.findMany({
      where: { hotelId: hotel.id },
      orderBy: { createdAt: 'desc' },
    }),
    prisma.hotelSetting.findMany({ where: { hotelId: hotel.id } }),
  ])

  const settingsMap = Object.fromEntries(settings.map(s => [s.key, s.value]))
  return { hotel, content, feedback, leads, settingsMap }
}

const CONTENT_TYPE_ICONS: Record<string, string> = {
  SOCIAL_POST: '📱', EMAIL: '✉️', BLOG: '📝', OFFER: '🎁', TEMPLATE: '📄',
}

const STATUS_STYLES: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-600',
  SCHEDULED: 'bg-blue-50 text-blue-700 border border-blue-200',
  PUBLISHED: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  ARCHIVED: 'bg-gray-50 text-gray-400',
}

const LEAD_STATUS_STYLES: Record<string, string> = {
  NEW: 'bg-amber-50 text-amber-800 border border-amber-200',
  CONTACTED: 'bg-blue-50 text-blue-700 border border-blue-200',
  QUOTED: 'bg-purple-50 text-purple-700 border border-purple-200',
  CONFIRMED: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  LOST: 'bg-gray-100 text-gray-500',
}

export default async function MarketingPage() {
  const data = await getData()
  if (!data) return null
  const { content, feedback, leads, settingsMap } = data

  const publishedContent = content.filter(c => c.status === 'PUBLISHED')
  const draftContent = content.filter(c => c.status === 'DRAFT')
  const newLeads = leads.filter(l => l.status === 'NEW')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="section-title">Marketing</h1>
        <p className="section-subtitle">Content, direct leads, and guest testimonials</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Published', value: publishedContent.length, color: 'text-emerald-600' },
          { label: 'Drafts', value: draftContent.length, color: 'text-[#667085]' },
          { label: 'Direct Leads', value: leads.length, color: 'text-[#1E2761]' },
          { label: 'New Leads', value: newLeads.length, color: 'text-[#C9A84C]' },
        ].map(s => (
          <div key={s.label} className="stat-card text-center">
            <div className={cn('font-serif text-3xl font-bold', s.color)}>{s.value}</div>
            <div className="text-xs text-[#667085] mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Direct booking leads */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-serif text-lg text-[#1E2761]">Direct Booking Leads</h2>
          {newLeads.length > 0 && (
            <span className="badge bg-amber-50 text-amber-800 border border-amber-200">{newLeads.length} new</span>
          )}
        </div>
        <div className="data-card divide-y divide-[#E4E8F1]">
          {leads.map(lead => (
            <div key={lead.id} className="px-4 py-4 flex items-start gap-4">
              <div className="w-9 h-9 rounded-full bg-[#1E2761]/10 text-[#1E2761] font-bold text-sm flex items-center justify-center flex-shrink-0">
                {lead.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-[#182033]">{lead.name}</span>
                  <span className={cn('badge text-[10px]', LEAD_STATUS_STYLES[lead.status])}>{lead.status}</span>
                  {lead.source && (
                    <span className="text-[10px] text-[#667085] bg-[#F5F7FB] px-1.5 py-0.5 rounded">via {lead.source}</span>
                  )}
                </div>
                <div className="text-xs text-[#667085] mt-0.5">
                  {lead.checkIn && lead.checkOut && (
                    <span>{new Date(lead.checkIn).toLocaleDateString('en-GB', { day:'numeric', month:'short', year:'numeric' })} → {new Date(lead.checkOut).toLocaleDateString('en-GB', { day:'numeric', month:'short', year:'numeric' })} · {lead.adults} adult{lead.adults !== 1 ? 's' : ''}</span>
                  )}
                </div>
                {lead.message && (
                  <p className="text-xs text-[#667085] mt-1 italic">"{lead.message.slice(0, 120)}{lead.message.length > 120 ? '...' : ''}"</p>
                )}
                <div className="text-[10px] text-[#667085] mt-1">
                  {lead.email} {lead.phone && `· ${lead.phone}`} · {friendlyDate(lead.createdAt)}
                </div>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <button className="text-[10px] bg-[#1E2761] text-white px-3 py-1.5 rounded-lg hover:bg-[#243070] font-semibold">
                  Reply
                </button>
                <button className="text-[10px] border border-[#E4E8F1] text-[#667085] px-3 py-1.5 rounded-lg hover:bg-gray-50">
                  Quote
                </button>
              </div>
            </div>
          ))}
          {leads.length === 0 && (
            <div className="px-4 py-8 text-center text-[#667085] text-sm">No direct leads yet</div>
          )}
        </div>
      </div>

      {/* AI content ideas */}
      <div className="data-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-6 h-6 rounded-lg bg-[#1E2761] flex items-center justify-center">
            <span className="text-[#C9A84C] text-[10px] font-bold">AI</span>
          </div>
          <span className="font-semibold text-sm text-[#182033]">Content Ideas — This Week</span>
        </div>
        <div className="space-y-3">
          {[
            { platform: 'Instagram', type: '📸 Photo Post', idea: 'Rooftop sunrise over Phnom Penh — guests love the views. Caption: "Wake up to this every morning at A Z Hotel. Book your stay →"', tag: 'High engagement' },
            { platform: 'Facebook', type: '🎁 Promotion', idea: 'Weekend escape package: 2 nights + late checkout + welcome drink. Target: expats and weekend travelers from Bangkok/HCMC.', tag: 'Revenue driver' },
            { platform: 'Email', type: '✉️ Newsletter', idea: 'Guest spotlight: share a curated snippet of your Local Guide with subscribers. "Our top 5 spots for Khmer coffee this season."', tag: 'Retention' },
            { platform: 'Google', type: '🗺️ Profile Post', idea: 'Post a "This week at A Z Hotel" update on Google Business Profile with current promotions and any events nearby.', tag: 'SEO boost' },
          ].map((idea, i) => (
            <div key={i} className="flex items-start gap-3 p-3 bg-[#F5F7FB] rounded-xl">
              <span className="text-lg">{idea.type.split(' ')[0]}</span>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-semibold text-[#182033]">{idea.platform}</span>
                  <span className="text-[10px] bg-[#C9A84C]/10 text-[#A66E00] px-1.5 py-0.5 rounded">{idea.tag}</span>
                </div>
                <p className="text-xs text-[#667085] leading-relaxed">{idea.idea}</p>
              </div>
              <button className="text-[10px] px-2.5 py-1 rounded-lg border border-[#E4E8F1] text-[#667085] hover:bg-white flex-shrink-0">Use</button>
            </div>
          ))}
        </div>
      </div>

      {/* Testimonials */}
      {feedback.length > 0 && (
        <div>
          <h2 className="font-serif text-lg text-[#1E2761] mb-3">Guest Testimonials</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {feedback.map(f => (
              <div key={f.id} className="data-card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-7 h-7 rounded-full bg-emerald-100 text-emerald-700 font-bold text-xs flex items-center justify-center">
                    {f.guest?.firstName[0]}{f.guest?.lastName[0]}
                  </div>
                  <div>
                    <div className="font-semibold text-xs text-[#182033]">{f.guest?.firstName} {f.guest?.lastName}</div>
                    <div className="text-[10px] text-[#667085]">
                      {'★'.repeat(f.rating || 0)}{'☆'.repeat(5 - (f.rating || 0))} · {friendlyDate(f.createdAt)}
                    </div>
                  </div>
                </div>
                <p className="text-xs text-[#182033] italic leading-relaxed">"{f.comment}"</p>
                <div className="flex gap-2 mt-3">
                  <button className="text-[10px] border border-[#E4E8F1] text-[#667085] px-2.5 py-1 rounded-lg hover:bg-gray-50">Copy for social</button>
                  <button className="text-[10px] border border-[#E4E8F1] text-[#667085] px-2.5 py-1 rounded-lg hover:bg-gray-50">Add to website</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Content library */}
      <div>
        <h2 className="font-serif text-lg text-[#1E2761] mb-3">Content Library</h2>
        <div className="space-y-2">
          {content.map(item => (
            <div key={item.id} className="data-card px-4 py-3 flex items-start gap-3">
              <span className="text-lg flex-shrink-0">{CONTENT_TYPE_ICONS[item.type] || '📄'}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-sm text-[#182033]">{item.title}</span>
                  <span className={cn('badge text-[10px]', STATUS_STYLES[item.status])}>{item.status}</span>
                  <span className="text-[10px] text-[#667085]">{item.platform}</span>
                </div>
                <p className="text-xs text-[#667085] mt-0.5 line-clamp-2">{item.content}</p>
                {item.publishDate && (
                  <div className="text-[10px] text-[#667085] mt-1">Publish: {friendlyDate(item.publishDate)}</div>
                )}
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <button className="text-[10px] px-2.5 py-1 rounded-lg border border-[#E4E8F1] text-[#667085] hover:bg-gray-50">Edit</button>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-3">
          <button className="text-sm text-[#1E2761] border border-[#1E2761] px-4 py-2 rounded-lg hover:bg-[#1E2761]/5 transition-colors">
            + New Content
          </button>
        </div>
      </div>

      {/* WhatsApp quick-share */}
      {settingsMap.whatsapp_number && (
        <div className="data-card p-4 bg-[#F5F7FB]">
          <div className="flex items-center gap-3">
            <span className="text-2xl">💬</span>
            <div className="flex-1">
              <div className="font-semibold text-sm text-[#182033]">WhatsApp Direct Line</div>
              <div className="text-xs text-[#667085]">{settingsMap.whatsapp_number} · Active for guest inquiries and direct bookings</div>
            </div>
            <button className="text-xs bg-emerald-600 text-white px-3 py-1.5 rounded-lg hover:bg-emerald-700">
              Open Chat
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
