import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/db'

export async function PATCH(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const body = await req.json()
  const room = await prisma.room.update({
    where: { id: params.id },
    data: { ...body, updatedAt: new Date() },
  })
  return NextResponse.json(room)
}
