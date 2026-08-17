import { prisma } from '@/lib/db'
import { CATEGORY_LABELS, CATEGORY_ICONS } from '@/lib/utils'

export const dynamic = 'force-dynamic'
export const metadata = { title: 'Local Guide' }

async function getData() {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return null

  const recommendations = await prisma.localRecommendation.findMany({
    where: { hotelId: hotel.id, isActive: true },
    orderBy: [{ category: 'asc' }, { sortOrder: 'asc' }],
  })
  return { hotel, recommendations }
}

export default async function LocalGuidePage() {
  const data = await getData()
  if (!data) return null
  const { recommendations } = data

  const byCategory = recommendations.reduce((acc, rec) => {
    if (!acc[rec.category]) acc[rec.category] = []
    acc[rec.category].push(rec)
    return acc
  }, {} as Record<string, typeof recommendations>)

  const categoryOrder = ['eat', 'coffee', 'drinks', 'essentials', 'pharmacy', 'sim', 'laundry', 'transport', 'attractions', 'late_night', 'tips']

  return (
    <div className="space-y-6">
      <div>
        <h1 className="section-title">A Z Local Guide</h1>
        <p className="section-subtitle">Curated Phnom Penh recommendations · {recommendations.length} places</p>
      </div>

      {/* Category pills */}
      <div className="flex flex-wrap gap-2">
        {categoryOrder.filter(c => byCategory[c]).map(cat => (
          <a key={cat} href={`#${cat}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white border border-[#E4E8F1] text-sm text-[#182033] hover:border-[#1E2761] hover:text-[#1E2761] transition-colors">
            <span>{CATEGORY_ICONS[cat]}</span>
            <span>{CATEGORY_LABELS[cat]}</span>
            <span className="text-[#667085] text-xs">({byCategory[cat].length})</span>
          </a>
        ))}
      </div>

      {/* Categories */}
      {categoryOrder.filter(c => byCategory[c]).map(cat => (
        <div key={cat} id={cat}>
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">{CATEGORY_ICONS[cat]}</span>
            <h2 className="font-serif text-xl text-[#1E2761]">{CATEGORY_LABELS[cat]}</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {byCategory[cat].map(rec => (
              <div key={rec.id} className="data-card p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3 className="font-semibold text-[#182033]">{rec.name}</h3>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {rec.priceRange && (
                      <span className="text-xs text-[#667085] bg-gray-50 px-1.5 py-0.5 rounded">{rec.priceRange}</span>
                    )}
                  </div>
                </div>
                <p className="text-sm text-[#667085] leading-relaxed mb-3">{rec.description}</p>
                {(rec.distance || rec.hours || rec.address) && (
                  <div className="space-y-1 mb-3">
                    {rec.distance && (
                      <div className="text-xs text-[#667085] flex items-center gap-1.5">
                        <span>📍</span> {rec.distance}
                        {rec.transport && ` · ${rec.transport}`}
                      </div>
                    )}
                    {rec.hours && (
                      <div className="text-xs text-[#667085] flex items-center gap-1.5">
                        <span>🕐</span> {rec.hours}
                      </div>
                    )}
                    {rec.address && (
                      <div className="text-xs text-[#667085] flex items-center gap-1.5">
                        <span>🗺️</span> {rec.address}
                      </div>
                    )}
                  </div>
                )}
                {rec.hotelNote && (
                  <div className="bg-[#FFF8E7] border border-[#C9A84C]/20 rounded-lg p-2 text-xs text-[#A66E00] leading-relaxed">
                    <span className="font-semibold">A Z recommends:</span> {rec.hotelNote}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
