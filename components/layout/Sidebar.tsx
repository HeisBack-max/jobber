'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  BedDouble,
  Users,
  Bell,
  Sparkles,
  Wrench,
  Star,
  Map,
  BarChart3,
  Megaphone,
  Settings,
  QrCode,
  Building2,
} from 'lucide-react'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/rooms', label: 'Rooms', icon: BedDouble },
  { href: '/guests', label: 'Guests', icon: Users },
  { href: '/requests', label: 'Requests', icon: Bell },
  { href: '/housekeeping', label: 'Housekeeping', icon: Sparkles },
  { href: '/maintenance', label: 'Maintenance', icon: Wrench },
  { href: '/reputation', label: 'Reputation', icon: Star },
  { href: '/local', label: 'Local Guide', icon: Map },
  { href: '/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/marketing', label: 'Marketing', icon: Megaphone },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed inset-y-0 left-0 w-56 flex flex-col z-30 select-none"
      style={{ background: 'linear-gradient(180deg, #121A45 0%, #1a2358 100%)' }}>
      {/* Logo */}
      <div className="px-5 pt-6 pb-4">
        <div className="flex items-center gap-2.5 mb-1">
          <div className="w-8 h-8 rounded-lg bg-[#C9A84C]/20 border border-[#C9A84C]/30 flex items-center justify-center">
            <Building2 className="w-4 h-4 text-[#C9A84C]" />
          </div>
          <div>
            <div className="text-white font-bold text-sm tracking-wider">A Z HOTEL</div>
            <div className="text-[#CADCFC] text-[9px] tracking-widest uppercase">Growth OS</div>
          </div>
        </div>
        <div className="mt-3 px-0.5 py-2 border-t border-white/10">
          <div className="text-[#667085] text-[10px] uppercase tracking-wider">Phnom Penh</div>
          <div className="text-[#C9A84C] text-xs font-medium">Management View</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 pb-4 space-y-0.5 overflow-y-auto">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== '/dashboard' && pathname.startsWith(href))
          return (
            <Link key={href} href={href}
              className={cn(
                'nav-item group',
                active && 'active'
              )}>
              <Icon className={cn('w-4 h-4 flex-shrink-0', active ? 'text-[#C9A84C]' : 'text-gray-400 group-hover:text-gray-200')} />
              <span>{label}</span>
              {href === '/requests' && (
                <span className="ml-auto bg-amber-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">3</span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Bottom links */}
      <div className="px-3 pb-5 space-y-0.5 border-t border-white/10 pt-3">
        <Link href="/guest" target="_blank"
          className="nav-item text-[#C9A84C] hover:text-[#E8C96A] hover:bg-[#C9A84C]/10">
          <QrCode className="w-4 h-4 flex-shrink-0" />
          <span>Guest Companion</span>
        </Link>
        <Link href="/settings"
          className={cn('nav-item', pathname === '/settings' && 'active')}>
          <Settings className="w-4 h-4 flex-shrink-0 text-gray-400" />
          <span>Settings</span>
        </Link>
        <div className="px-3 pt-3">
          <div className="text-[10px] text-[#667085]">Logged in as</div>
          <div className="text-white text-xs font-medium">Sophal Meas</div>
          <div className="text-[#667085] text-[10px]">Manager</div>
        </div>
      </div>
    </aside>
  )
}
