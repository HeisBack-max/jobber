import { prisma } from '@/lib/db'
import { format } from 'date-fns'
import GuestCompanionClient from './GuestCompanionClient'

export const dynamic = 'force-dynamic'
export const metadata = { title: 'A Z Hotel · Guest Companion' }

async function getGuestData(token: string | null) {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return null

  let stay = null
  if (token) {
    stay = await prisma.stay.findUnique({
      where: { guestToken: token },
      include: {
        guest: true,
        room: true,
      },
    })
  }

  const recommendations = await prisma.localRecommendation.findMany({
    where: { hotelId: hotel.id, isActive: true },
    orderBy: [{ category: 'asc' }, { sortOrder: 'asc' }],
    take: 15,
  })

  return { hotel, stay, recommendations }
}

export default async function GuestPage({
  searchParams,
}: {
  searchParams: { token?: string; lang?: string }
}) {
  const token = searchParams.token || null
  const lang = (searchParams.lang as 'en' | 'km' | 'zh') || 'en'

  const data = await getGuestData(token)
  if (!data) return <div className="p-8 text-center text-gray-500">Hotel not found</div>

  const { hotel, stay, recommendations } = data

  const guestFirstName = stay?.guest?.firstName || null
  const roomNumber = stay?.room?.number || null
  const checkOutDate = stay?.checkOut ? format(new Date(stay.checkOut), 'd MMM yyyy') : null

  return (
    <GuestCompanionClient
      hotelName={hotel.name}
      wifiName={hotel.wifiName || ''}
      wifiPassword={hotel.wifiPassword || ''}
      checkInTime={hotel.checkInTime || '14:00'}
      checkOutTime={hotel.checkOutTime || '12:00'}
      phone={hotel.phone || ''}
      guestFirstName={guestFirstName}
      roomNumber={roomNumber}
      checkOutDate={checkOutDate}
      stayToken={token}
      recommendations={recommendations.map(r => ({
        id: r.id,
        category: r.category,
        name: r.name,
        description: r.description,
        distance: r.distance,
        hours: r.hours,
        priceRange: r.priceRange,
        hotelNote: r.hotelNote,
      }))}
      lang={lang}
    />
  )
}
