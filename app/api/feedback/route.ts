import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/db'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { rating, comment, token } = body

    const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
    if (!hotel) return NextResponse.json({ error: 'Not found' }, { status: 404 })

    let stayId: string | undefined
    let guestId: string | undefined

    if (token) {
      const stay = await prisma.stay.findUnique({
        where: { guestToken: token },
        include: { guest: true },
      })
      if (stay) {
        stayId = stay.id
        guestId = stay.guestId
      }
    }

    const sentiment = rating >= 4 ? 'POSITIVE' : rating === 3 ? 'NEUTRAL' : 'NEGATIVE'
    const isRecoveryCase = rating !== null && rating <= 2

    const feedback = await prisma.guestFeedback.create({
      data: {
        hotelId: hotel.id,
        stayId: stayId || null,
        guestId: guestId || null,
        rating: rating || null,
        comment: comment || null,
        sentiment,
        category: 'general',
        isRecoveryCase,
        isResolved: false,
      },
    })

    return NextResponse.json({ id: feedback.id })
  } catch (e) {
    console.error(e)
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}
