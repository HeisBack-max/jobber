'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'

type Task = {
  id: string; type: string; status: string; priority: string
  assignedTo: string; notes: string; scheduledFor: Date | null
  guestInstruction: string
  room: { number: string; type: string }
}

const TYPE_LABELS: Record<string, string> = {
  FULL_CLEAN: 'Full Clean', CHECKOUT_CLEAN: 'Checkout Clean', DAILY_CLEAN: 'Daily Clean',
  TURNDOWN: 'Turndown', TOWELS_ONLY: 'Towels Only', INSPECTION: 'Inspection', WELCOME_SETUP: 'Welcome Setup',
}

const INSTRUCTION_LABELS: Record<string, string> = {
  CLEAN_NOW: '🟢 Clean Now', CLEAN_LATER: '🕐 Later', DND: '🔴 DND', TOWELS_ONLY: '🟡 Towels',
}

export default function HousekeepingTaskRow({ task }: { task: Task }) {
  const [status, setStatus] = useState(task.status)
  const [loading, setLoading] = useState(false)

  const advance = async () => {
    const next = status === 'PENDING' ? 'IN_PROGRESS' : status === 'IN_PROGRESS' ? 'COMPLETED' : null
    if (!next) return
    setLoading(true)
    try {
      const res = await fetch(`/api/housekeeping/${task.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: next }),
      })
      if (res.ok) setStatus(next)
    } finally {
      setLoading(false)
    }
  }

  const next = status === 'PENDING' ? 'Start' : status === 'IN_PROGRESS' ? 'Complete' : null

  return (
    <tr className={cn(
      'hover:bg-[#F5F7FB] transition-colors',
      task.priority === 'HIGH' && status !== 'COMPLETED' && 'bg-amber-50/30',
    )}>
      <td className="table-cell">
        <div className="font-bold text-[#1E2761]">{task.room.number}</div>
        <div className="text-[10px] text-[#667085]">{task.room.type}</div>
      </td>
      <td className="table-cell">
        <div className="flex items-center gap-1.5">
          {task.priority === 'HIGH' && <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />}
          <span className="font-medium text-sm text-[#182033]">{TYPE_LABELS[task.type] || task.type}</span>
        </div>
        <div className={cn('text-[10px] mt-0.5',
          status === 'PENDING' ? 'text-amber-600' : status === 'IN_PROGRESS' ? 'text-blue-600' : 'text-emerald-600'
        )}>
          {status.replace('_', ' ')}
        </div>
      </td>
      <td className="table-cell text-xs">
        {task.guestInstruction ? (
          <span className="text-xs">{INSTRUCTION_LABELS[task.guestInstruction] || task.guestInstruction}</span>
        ) : (
          <span className="text-[#667085]">—</span>
        )}
      </td>
      <td className="table-cell text-xs text-[#667085]">{task.assignedTo || '—'}</td>
      <td className="table-cell text-xs text-[#667085] whitespace-nowrap">
        {task.scheduledFor ? format(new Date(task.scheduledFor), 'HH:mm') : '—'}
      </td>
      <td className="table-cell text-xs text-[#667085] max-w-[160px]">
        <span className="line-clamp-2">{task.notes || '—'}</span>
      </td>
      <td className="table-cell">
        {next ? (
          <button
            onClick={advance}
            disabled={loading}
            className="text-[10px] px-2.5 py-1.5 rounded-lg bg-[#1E2761] text-white hover:bg-[#243070] disabled:opacity-50 transition-colors font-semibold"
          >
            {loading ? '...' : next}
          </button>
        ) : (
          <span className="text-[10px] text-emerald-600">✓ Done</span>
        )}
      </td>
    </tr>
  )
}
