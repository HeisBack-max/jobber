import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/db'

export async function GET() {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return NextResponse.json({ error: 'Not found' }, { status: 404 })

  const leads = await prisma.directBookingLead.findMany({
    where: { hotelId: hotel.id },
    orderBy: { createdAt: 'desc' },
  })

  return NextResponse.json(leads)
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { name, email, phone, checkIn, checkOut, adults, message, source } = body

    if (!name || !email) {
      return NextResponse.json({ error: 'Name and email are required' }, { status: 400 })
    }

    const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
    if (!hotel) return NextResponse.json({ error: 'Not found' }, { status: 404 })

    const lead = await prisma.directBookingLead.create({
      data: {
        hotelId: hotel.id,
        name,
        email,
        phone: phone || null,
        checkIn: checkIn ? new Date(checkIn) : null,
        checkOut: checkOut ? new Date(checkOut) : null,
        adults: adults || 1,
        message: message || null,
        status: 'NEW',
        source: source || 'website',
      },
    })

    return NextResponse.json({ id: lead.id })
  } catch (e) {
    console.error(e)
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}

export async function PATCH(req: NextRequest) {
  try {
    const body = await req.json()
    const { id, status, notes } = body

    const lead = await prisma.directBookingLead.update({
      where: { id },
      data: {
        ...(status && { status }),
        ...(notes && { notes }),
      },
    })

    return NextResponse.json(lead)
  } catch (e) {
    console.error(e)
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}
