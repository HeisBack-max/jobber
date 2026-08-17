'use client'

import { useState } from 'react'
import { cn, PRIORITY_COLORS, STATUS_COLORS, friendlyDate } from '@/lib/utils'

type Request = {
  id: string; priority: string; category: string; description: string
  status: string; assignedTo: string; createdAt: Date
  room: { number: string } | null
  guest: { firstName: string; lastName: string } | null
}

const nextStatus: Record<string, string> = {
  NEW: 'ACCEPTED', ACCEPTED: 'IN_PROGRESS', IN_PROGRESS: 'COMPLETED', WAITING: 'IN_PROGRESS', ESCALATED: 'IN_PROGRESS',
}

export default function RequestRow({ request }: { request: Request }) {
  const [status, setStatus] = useState(request.status)
  const [loading, setLoading] = useState(false)

  const advance = async () => {
    const next = nextStatus[status]
    if (!next) return
    setLoading(true)
    try {
      const res = await fetch(`/api/requests/${request.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: next }),
      })
      if (res.ok) setStatus(next)
    } finally {
      setLoading(false)
    }
  }

  const next = nextStatus[status]

  return (
    <tr className={cn(
      'hover:bg-[#F5F7FB] transition-colors',
      request.priority === 'HIGH' && 'bg-amber-50/30',
      request.priority === 'URGENT' && 'bg-red-50/30',
    )}>
      <td className="table-cell">
        <span className={cn('badge text-[10px]', PRIORITY_COLORS[request.priority])}>
          {request.priority}
        </span>
      </td>
      <td className="table-cell font-medium text-[#182033]">{request.category}</td>
      <td className="table-cell text-[#667085] max-w-xs">
        <span className="line-clamp-2">{request.description}</span>
        {request.guest && (
          <div className="text-[10px] text-[#667085] mt-0.5">{request.guest.firstName} {request.guest.lastName}</div>
        )}
      </td>
      <td className="table-cell">
        {request.room && (
          <span className="badge bg-[#1E2761]/5 text-[#1E2761]">Room {request.room.number}</span>
        )}
      </td>
      <td className="table-cell text-[#667085] text-xs whitespace-nowrap">{friendlyDate(request.createdAt)}</td>
      <td className="table-cell">
        <span className={cn('badge text-[10px]', STATUS_COLORS[status])}>{status.replace('_', ' ')}</span>
      </td>
      <td className="table-cell">
        {next ? (
          <button
            onClick={advance}
            disabled={loading}
            className="text-[10px] px-2.5 py-1.5 rounded-lg bg-[#1E2761] text-white hover:bg-[#243070] disabled:opacity-50 transition-colors font-semibold whitespace-nowrap"
          >
            {loading ? '...' : `→ ${next.replace('_', ' ')}`}
          </button>
        ) : (
          <span className="text-[10px] text-[#667085]">Done</span>
        )}
      </td>
    </tr>
  )
}
