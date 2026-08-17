'use client'

import { useState } from 'react'
import { cn, STATUS_COLORS } from '@/lib/utils'

const nextStatus: Record<string, string> = {
  NEW: 'ACCEPTED',
  ACCEPTED: 'IN_PROGRESS',
  IN_PROGRESS: 'COMPLETED',
  WAITING: 'IN_PROGRESS',
  ESCALATED: 'IN_PROGRESS',
}

export default function RequestUpdateButton({ id, currentStatus }: { id: string; currentStatus: string }) {
  const [status, setStatus] = useState(currentStatus)
  const [loading, setLoading] = useState(false)

  const next = nextStatus[status]
  if (!next || status === 'COMPLETED') return (
    <span className={cn('badge text-[10px]', STATUS_COLORS[status])}>{status.replace('_', ' ')}</span>
  )

  const advance = async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/requests/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: next }),
      })
      if (res.ok) setStatus(next)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <span className={cn('badge text-[10px]', STATUS_COLORS[status])}>{status.replace('_', ' ')}</span>
      <button
        onClick={advance}
        disabled={loading}
        className="text-[10px] px-2 py-1 rounded-lg bg-[#1E2761] text-white hover:bg-[#243070] disabled:opacity-50 transition-colors font-semibold"
      >
        {loading ? '...' : `→ ${next.replace('_', ' ')}`}
      </button>
    </div>
  )
}
