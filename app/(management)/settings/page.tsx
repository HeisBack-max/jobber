import { prisma } from '@/lib/db'

export const dynamic = 'force-dynamic'
export const metadata = { title: 'Settings' }

async function getData() {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return null

  const [settings, users] = await Promise.all([
    prisma.hotelSetting.findMany({ where: { hotelId: hotel.id } }),
    prisma.user.findMany({ where: { hotelId: hotel.id, isActive: true }, orderBy: { name: 'asc' } }),
  ])

  const settingsMap = Object.fromEntries(settings.map(s => [s.key, s.value]))
  return { hotel, settingsMap, users }
}

const ROLE_LABELS: Record<string, string> = {
  MANAGER: 'Manager', FRONT_DESK: 'Front Desk', HOUSEKEEPING: 'Housekeeping', MAINTENANCE: 'Maintenance',
}

export default async function SettingsPage() {
  const data = await getData()
  if (!data) return null
  const { hotel, settingsMap, users } = data

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="section-title">Settings</h1>
        <p className="section-subtitle">Hotel configuration and team management</p>
      </div>

      {/* Hotel info */}
      <div className="data-card p-5">
        <h2 className="font-serif text-lg text-[#1E2761] mb-4">Hotel Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { label: 'Hotel Name', value: hotel.name },
            { label: 'City', value: hotel.city },
            { label: 'Country', value: hotel.country },
            { label: 'Phone', value: hotel.phone },
            { label: 'Email', value: hotel.email },
            { label: 'Currency', value: hotel.currency },
            { label: 'Timezone', value: hotel.timezone },
            { label: 'Check-in Time', value: hotel.checkInTime },
            { label: 'Check-out Time', value: hotel.checkOutTime },
          ].filter(f => f.value).map(field => (
            <div key={field.label}>
              <label className="block text-xs text-[#667085] mb-1">{field.label}</label>
              <div className="input-field bg-[#F5F7FB] text-[#182033]">{field.value}</div>
            </div>
          ))}
          <div className="md:col-span-2">
            <label className="block text-xs text-[#667085] mb-1">Address</label>
            <div className="input-field bg-[#F5F7FB] text-[#182033]">{hotel.address}</div>
          </div>
        </div>
        <button className="mt-4 btn-primary text-sm">Save Changes</button>
      </div>

      {/* Connectivity */}
      <div className="data-card p-5">
        <h2 className="font-serif text-lg text-[#1E2761] mb-4">Guest Connectivity</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-[#667085] mb-1">WiFi Network Name</label>
            <div className="input-field bg-[#F5F7FB] text-[#182033]">{hotel.wifiName || '–'}</div>
          </div>
          <div>
            <label className="block text-xs text-[#667085] mb-1">WiFi Password</label>
            <div className="input-field bg-[#F5F7FB] text-[#182033] font-mono">{hotel.wifiPassword || '–'}</div>
          </div>
          <div>
            <label className="block text-xs text-[#667085] mb-1">WhatsApp Number</label>
            <div className="input-field bg-[#F5F7FB] text-[#182033]">{settingsMap.whatsapp_number || '–'}</div>
          </div>
          <div>
            <label className="block text-xs text-[#667085] mb-1">Emergency Contact</label>
            <div className="input-field bg-[#F5F7FB] text-[#182033]">{settingsMap.emergency_contact || '–'}</div>
          </div>
        </div>
      </div>

      {/* Platform ratings */}
      <div className="data-card p-5">
        <h2 className="font-serif text-lg text-[#1E2761] mb-4">Platform Review Scores</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { platform: 'Google', ratingKey: 'google_rating', countKey: 'google_review_count', max: '/ 5.0' },
            { platform: 'Booking.com', ratingKey: 'booking_rating', countKey: 'booking_review_count', max: '/ 10.0' },
            { platform: 'TripAdvisor', ratingKey: 'tripadvisor_rating', countKey: 'tripadvisor_review_count', max: '/ 5.0' },
          ].map(p => (
            <div key={p.platform}>
              <label className="block text-xs text-[#667085] mb-1">{p.platform}</label>
              <div className="flex gap-2">
                <div className="input-field bg-[#F5F7FB] text-[#182033] flex-1 font-semibold">
                  {settingsMap[p.ratingKey] || '–'} <span className="text-[#667085] font-normal text-xs">{p.max}</span>
                </div>
                <div className="input-field bg-[#F5F7FB] text-[#667085] w-20 text-xs">
                  {settingsMap[p.countKey] || '–'} rev.
                </div>
              </div>
            </div>
          ))}
        </div>
        <p className="text-xs text-[#667085] mt-3">Update these scores manually from your platform dashboards. They appear on the Reputation and Analytics pages.</p>
      </div>

      {/* Team */}
      <div className="data-card overflow-hidden">
        <div className="px-5 py-3 border-b border-[#E4E8F1] bg-[#F5F7FB]">
          <h2 className="font-serif text-lg text-[#1E2761]">Team Members</h2>
        </div>
        <div className="divide-y divide-[#E4E8F1]">
          {users.map(user => (
            <div key={user.id} className="px-5 py-3 flex items-center gap-4">
              <div className="w-8 h-8 rounded-full bg-[#1E2761]/10 text-[#1E2761] font-bold text-sm flex items-center justify-center flex-shrink-0">
                {user.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
              </div>
              <div className="flex-1">
                <div className="font-medium text-sm text-[#182033]">{user.name}</div>
                <div className="text-xs text-[#667085]">{user.email}</div>
              </div>
              <div className="flex items-center gap-2">
                <span className="badge bg-[#1E2761]/5 text-[#1E2761] text-[10px]">
                  {ROLE_LABELS[user.role] || user.role}
                </span>
                {user.department && (
                  <span className="text-[10px] text-[#667085]">{user.department}</span>
                )}
              </div>
              <button className="text-[10px] border border-[#E4E8F1] text-[#667085] px-2.5 py-1 rounded-lg hover:bg-gray-50">Edit</button>
            </div>
          ))}
        </div>
        <div className="px-5 py-3 border-t border-[#E4E8F1]">
          <button className="text-sm text-[#1E2761] border border-[#1E2761] px-4 py-2 rounded-lg hover:bg-[#1E2761]/5 transition-colors">
            + Add Team Member
          </button>
        </div>
      </div>

      {/* Guest companion config */}
      <div className="data-card p-5">
        <h2 className="font-serif text-lg text-[#1E2761] mb-4">Guest Companion</h2>
        <p className="text-sm text-[#667085] mb-4">
          The Guest Companion is a mobile-first web app available at <code className="bg-[#F5F7FB] px-1.5 py-0.5 rounded text-xs text-[#182033]">/guest</code>. Guests access it via QR code at the front desk or in their room.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-3 bg-[#F5F7FB] rounded-xl">
            <div className="text-xs font-semibold text-[#182033] mb-1">Languages supported</div>
            <div className="text-xs text-[#667085]">English · ខ្មែរ (Khmer) · 简体中文 (Chinese)</div>
          </div>
          <div className="p-3 bg-[#F5F7FB] rounded-xl">
            <div className="text-xs font-semibold text-[#182033] mb-1">Guest URL</div>
            <div className="text-xs text-[#667085] font-mono">/guest?token=[stay-token]</div>
          </div>
        </div>
        <div className="mt-3 flex gap-2">
          <a href="/guest" target="_blank" rel="noreferrer"
            className="text-xs bg-[#C9A84C] text-[#121A45] px-3 py-1.5 rounded-lg hover:bg-[#E8C96A] font-semibold">
            Preview Guest Companion →
          </a>
        </div>
      </div>

      {/* Danger zone */}
      <div className="data-card p-5 border border-red-200">
        <h2 className="font-serif text-lg text-red-700 mb-2">Danger Zone</h2>
        <p className="text-sm text-[#667085] mb-4">These actions are irreversible. Proceed with caution.</p>
        <div className="flex gap-3">
          <button className="text-xs border border-red-200 text-red-700 px-3 py-1.5 rounded-lg hover:bg-red-50">
            Reset Demo Data
          </button>
          <button className="text-xs border border-red-200 text-red-700 px-3 py-1.5 rounded-lg hover:bg-red-50">
            Clear All Requests
          </button>
        </div>
      </div>
    </div>
  )
}
