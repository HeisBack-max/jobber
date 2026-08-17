import { prisma } from '@/lib/db'
import { cn, ROOM_STATUS_LABELS, ROOM_STATUS_COLORS } from '@/lib/utils'
import { BedDouble, AlertTriangle } from 'lucide-react'
import RoomStatusButton from '@/components/rooms/RoomStatusButton'

export const dynamic = 'force-dynamic'
export const metadata = { title: 'Rooms' }

async function getData() {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return null
  const rooms = await prisma.room.findMany({
    where: { hotelId: hotel.id },
    orderBy: { number: 'asc' },
    include: {
      stays: {
        where: { status: 'CHECKED_IN' },
        include: { guest: true },
      },
      housekeepingTasks: {
        where: { status: { in: ['PENDING', 'IN_PROGRESS'] } },
        take: 1,
      },
      maintenanceIssues: {
        where: { status: { in: ['OPEN', 'IN_PROGRESS'] } },
        take: 1,
      },
    },
  })
  return { hotel, rooms }
}

const STATUS_ORDER = ['OCCUPIED', 'VACANT_DIRTY', 'CLEANING', 'INSPECTION', 'MAINTENANCE', 'OUT_OF_SERVICE', 'VACANT_CLEAN']

export default async function RoomsPage() {
  const data = await getData()
  if (!data) return null
  const { rooms } = data

  const floors = [1, 2, 3, 4]
  const stats = {
    occupied: rooms.filter(r => r.status === 'OCCUPIED').length,
    clean: rooms.filter(r => r.status === 'VACANT_CLEAN').length,
    dirty: rooms.filter(r => r.status === 'VACANT_DIRTY').length,
    maintenance: rooms.filter(r => r.status === 'MAINTENANCE' || r.status === 'OUT_OF_SERVICE').length,
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="section-title">Rooms</h1>
        <p className="section-subtitle">{rooms.length} rooms across 4 floors</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Occupied', value: stats.occupied, color: 'bg-[#1E2761] text-white' },
          { label: 'Vacant Clean', value: stats.clean, color: 'bg-emerald-50 text-emerald-800 border border-emerald-200' },
          { label: 'Needs Cleaning', value: stats.dirty, color: 'bg-amber-50 text-amber-800 border border-amber-200' },
          { label: 'Maintenance', value: stats.maintenance, color: 'bg-red-50 text-red-700 border border-red-200' },
        ].map(s => (
          <div key={s.label} className="stat-card">
            <div className={cn('inline-flex items-center justify-center w-9 h-9 rounded-xl text-lg font-bold mb-2', s.color)}>
              {s.value}
            </div>
            <div className="text-xs text-[#667085]">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Floor grids */}
      {floors.map(floor => {
        const floorRooms = rooms.filter(r => r.floor === floor)
        return (
          <div key={floor} className="data-card p-4">
            <div className="flex items-center gap-3 mb-4">
              <h2 className="font-serif text-lg text-[#1E2761]">Floor {floor}</h2>
              <span className="text-xs text-[#667085]">
                {floorRooms.filter(r => r.status === 'OCCUPIED').length} occupied ·&nbsp;
                {floorRooms.filter(r => r.status === 'VACANT_CLEAN').length} clean ·&nbsp;
                {floorRooms.filter(r => r.type === 'Superior').length > 0 ? 'Superior' :
                 floorRooms.filter(r => r.type === 'Deluxe').length > 0 ? 'Deluxe' : 'Standard'} rooms
              </span>
            </div>
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
              {floorRooms.map(room => {
                const activeStay = room.stays[0]
                const hasMaintenance = room.maintenanceIssues.length > 0
                const hasHousekeeping = room.housekeepingTasks.length > 0
                return (
                  <div key={room.id} className="relative">
                    <div className={cn(
                      'room-tile border-2',
                      room.status === 'OCCUPIED' ? 'bg-[#1E2761] border-[#1E2761] text-white' :
                      room.status === 'VACANT_CLEAN' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' :
                      room.status === 'VACANT_DIRTY' ? 'bg-amber-50 border-amber-300 text-amber-800' :
                      room.status === 'CLEANING' ? 'bg-blue-50 border-blue-200 text-blue-800' :
                      room.status === 'INSPECTION' ? 'bg-purple-50 border-purple-200 text-purple-800' :
                      room.status === 'MAINTENANCE' ? 'bg-orange-50 border-orange-300 text-orange-800' :
                      'bg-gray-100 border-gray-300 text-gray-400'
                    )}>
                      <div className="font-bold text-base">{room.number}</div>
                      <div className="text-[9px] mt-0.5 leading-tight opacity-80">
                        {ROOM_STATUS_LABELS[room.status]?.split('—')[0].trim() || room.status}
                      </div>
                      {activeStay && (
                        <div className="text-[9px] mt-1 opacity-70 truncate">
                          {activeStay.guest.firstName}
                        </div>
                      )}
                      {(hasMaintenance || hasHousekeeping) && (
                        <div className="mt-1 flex justify-center gap-0.5">
                          {hasMaintenance && <span className="w-1.5 h-1.5 rounded-full bg-red-400" title="Maintenance issue" />}
                          {hasHousekeeping && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" title="Housekeeping pending" />}
                        </div>
                      )}
                    </div>
                    {room.status !== 'OCCUPIED' && room.status !== 'OUT_OF_SERVICE' && (
                      <RoomStatusButton roomId={room.id} currentStatus={room.status} />
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}

      {/* Legend */}
      <div className="flex flex-wrap gap-3 text-xs">
        {Object.entries(ROOM_STATUS_LABELS).map(([key, label]) => (
          <div key={key} className="flex items-center gap-1.5">
            <div className={cn('w-3 h-3 rounded-sm border',
              key === 'OCCUPIED' ? 'bg-[#1E2761] border-[#1E2761]' :
              key === 'VACANT_CLEAN' ? 'bg-emerald-100 border-emerald-300' :
              key === 'VACANT_DIRTY' ? 'bg-amber-100 border-amber-300' :
              key === 'CLEANING' ? 'bg-blue-100 border-blue-300' :
              key === 'INSPECTION' ? 'bg-purple-100 border-purple-300' :
              key === 'MAINTENANCE' ? 'bg-orange-100 border-orange-300' :
              'bg-gray-100 border-gray-300'
            )} />
            <span className="text-[#667085]">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
