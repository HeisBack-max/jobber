'use client'

import { format } from 'date-fns'
import { Bell, Search } from 'lucide-react'
import { useState } from 'react'

export default function TopBar() {
  const now = new Date()
  const hour = now.getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
  const [searchOpen, setSearchOpen] = useState(false)

  return (
    <header className="sticky top-0 z-20 bg-white border-b border-[#E4E8F1] px-6 py-3 flex items-center gap-4">
      <div className="flex-1">
        <div className="text-sm text-[#667085]">
          {greeting} · <span className="font-medium text-[#182033]">{format(new Date(), 'EEEE, d MMMM yyyy')}</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {searchOpen ? (
          <input
            autoFocus
            className="w-56 px-3 py-1.5 text-sm border border-[#E4E8F1] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1E2761]/20"
            placeholder="Search guests, rooms..."
            onBlur={() => setSearchOpen(false)}
          />
        ) : (
          <button
            onClick={() => setSearchOpen(true)}
            className="p-2 rounded-lg hover:bg-[#F5F7FB] text-[#667085] hover:text-[#182033] transition-colors"
          >
            <Search className="w-4 h-4" />
          </button>
        )}

        <button className="relative p-2 rounded-lg hover:bg-[#F5F7FB] text-[#667085] hover:text-[#182033] transition-colors">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-amber-500 rounded-full"></span>
        </button>

        <div className="w-8 h-8 rounded-full bg-[#1E2761] text-white text-xs font-bold flex items-center justify-center">
          SM
        </div>
      </div>
    </header>
  )
}
