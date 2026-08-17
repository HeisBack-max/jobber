'use client'

import { useState } from 'react'
import { cn, SEVERITY_COLORS, ISSUE_STATUS_COLORS, friendlyDate } from '@/lib/utils'

type Issue = {
  id: string; category: string; description: string; severity: string
  status: string; reportedBy: string; assignedTo: string; isRecurring: boolean
  createdAt: Date; room: { number: string } | null
}

const CATEGORY_ICONS: Record<string, string> = {
  ac: '❄️', plumbing: '🚰', electrical: '⚡', wifi: '📶',
  furniture: '🪑', bathroom: '🚿', door: '🚪', lighting: '💡', other: '🔧',
}

const nextStatus: Record<string, string> = {
  OPEN: 'IN_PROGRESS', IN_PROGRESS: 'RESOLVED',
}

export default function MaintenanceIssueRow({ issue }: { issue: Issue }) {
  const [status, setStatus] = useState(issue.status)
  const [loading, setLoading] = useState(false)

  const advance = async () => {
    const next = nextStatus[status]
    if (!next) return
    setLoading(true)
    try {
      const res = await fetch(`/api/maintenance/${issue.id}`, {
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
      issue.severity === 'CRITICAL' && 'bg-red-50/30',
      issue.severity === 'HIGH' && 'bg-amber-50/20',
    )}>
      <td className="table-cell">
        <span className={cn('badge text-[10px]', SEVERITY_COLORS[issue.severity])}>
          {issue.severity}
        </span>
        {issue.isRecurring && (
          <div className="text-[9px] text-amber-600 mt-0.5">⚠ Recurring</div>
        )}
      </td>
      <td className="table-cell">
        <div className="flex items-center gap-1.5">
          <span>{CATEGORY_ICONS[issue.category] || '🔧'}</span>
          <span className="font-medium text-sm capitalize">{issue.category}</span>
        </div>
      </td>
      <td className="table-cell text-[#667085] text-xs max-w-xs">
        <span className="line-clamp-2">{issue.description}</span>
        {issue.reportedBy && <div className="text-[10px] mt-0.5">Reported by: {issue.reportedBy}</div>}
      </td>
      <td className="table-cell">
        {issue.room ? (
          <span className="badge bg-[#1E2761]/5 text-[#1E2761]">Room {issue.room.number}</span>
        ) : (
          <span className="text-xs text-[#667085]">Common area</span>
        )}
      </td>
      <td className="table-cell text-xs text-[#667085] whitespace-nowrap">{friendlyDate(issue.createdAt)}</td>
      <td className="table-cell text-xs text-[#667085]">{issue.assignedTo || 'Unassigned'}</td>
      <td className="table-cell">
        <span className={cn('badge text-[10px]', ISSUE_STATUS_COLORS[status])}>{status.replace('_', ' ')}</span>
      </td>
      <td className="table-cell">
        {next ? (
          <button
            onClick={advance}
            disabled={loading}
            className="text-[10px] px-2.5 py-1.5 rounded-lg bg-[#1E2761] text-white hover:bg-[#243070] disabled:opacity-50 font-semibold whitespace-nowrap"
          >
            {loading ? '...' : next === 'IN_PROGRESS' ? '→ Start' : '→ Resolve'}
          </button>
        ) : (
          <span className="text-[10px] text-emerald-600">✓ Resolved</span>
        )}
      </td>
    </tr>
  )
}
