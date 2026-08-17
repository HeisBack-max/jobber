import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/db'

export async function PATCH(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const body = await req.json()
  const data: Record<string, unknown> = { ...body, updatedAt: new Date() }
  if (body.status === 'COMPLETED') data.completedAt = new Date()

  const task = await prisma.housekeepingTask.update({
    where: { id: params.id },
    data,
  })
  return NextResponse.json(task)
}
