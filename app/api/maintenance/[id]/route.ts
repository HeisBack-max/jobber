import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/db'

export async function PATCH(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const body = await req.json()
  const data: Record<string, unknown> = { ...body, updatedAt: new Date() }
  if (body.status === 'RESOLVED') data.resolvedAt = new Date()

  const issue = await prisma.maintenanceIssue.update({
    where: { id: params.id },
    data,
  })
  return NextResponse.json(issue)
}
