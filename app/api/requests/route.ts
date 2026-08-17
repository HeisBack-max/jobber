import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/db'

export async function GET() {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return NextResponse.json({ error: 'Hotel not found' }, { status: 404 })

  const requests = await prisma.serviceRequest.findMany({
    where: { hotelId: hotel.id },
    include: { room: true, guest: true },
    orderBy: [{ priority: 'desc' }, { createdAt: 'desc' }],
  })
  return NextResponse.json(requests)
}

export async function POST(req: NextRequest) {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return NextResponse.json({ error: 'Hotel not found' }, { status: 404 })

  const body = await req.json()

  let roomId = body.roomId || null
  let guestId = body.guestId || null

  if (body.token && !roomId) {
    const stay = await prisma.stay.findUnique({
      where: { guestToken: body.token },
    })
    if (stay) {
      roomId = stay.roomId || null
      guestId = stay.guestId || null
    }
  }

  const request = await prisma.serviceRequest.create({
    data: {
      hotelId: hotel.id,
      type: body.type || 'GUEST_REQUEST',
      category: body.category || 'room',
      description: body.description,
      priority: body.priority || 'NORMAL',
      status: 'NEW',
      roomId,
      guestId,
    },
  })
  return NextResponse.json(request, { status: 201 })
}
