'use client'

import { useState } from 'react'

const statuses = ['VACANT_DIRTY', 'CLEANING', 'INSPECTION', 'VACANT_CLEAN', 'MAINTENANCE']
const labels: Record<string, string> = {
  VACANT_DIRTY: 'Dirty', CLEANING: 'Cleaning', INSPECTION: 'Inspect',
  VACANT_CLEAN: 'Clean', MAINTENANCE: 'Maint.',
}

export default function RoomStatusButton({ roomId, currentStatus }: { roomId: string; currentStatus: string }) {
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useState(currentStatus)
  const [loading, setLoading] = useState(false)

  const update = async (newStatus: string) => {
    setLoading(true)
    setOpen(false)
    try {
      const res = await fetch(`/api/rooms/${roomId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      })
      if (res.ok) setStatus(newStatus)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative mt-1">
      <button
        onClick={() => setOpen(!open)}
        disabled={loading}
        className="w-full text-[9px] py-0.5 px-1 rounded bg-white/80 border border-gray-200 hover:bg-white text-[#667085] hover:text-[#182033] transition-colors"
      >
        {loading ? '...' : 'Change'}
      </button>
      {open && (
        <div className="absolute top-full left-0 right-0 z-50 mt-0.5 bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden">
          {statuses.filter(s => s !== status).map(s => (
            <button key={s} onClick={() => update(s)}
              className="block w-full text-left text-[10px] px-2 py-1.5 hover:bg-[#F5F7FB] text-[#182033]">
              {labels[s]}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
