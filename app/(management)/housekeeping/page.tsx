import { prisma } from '@/lib/db'
import { cn, friendlyDate } from '@/lib/utils'
import HousekeepingTaskRow from '@/components/housekeeping/HousekeepingTaskRow'

export const dynamic = 'force-dynamic'
export const metadata = { title: 'Housekeeping' }

async function getData() {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return null

  const [tasks, rooms] = await Promise.all([
    prisma.housekeepingTask.findMany({
      where: { hotelId: hotel.id },
      include: { room: true },
      orderBy: [{ priority: 'desc' }, { scheduledFor: 'asc' }],
    }),
    prisma.room.findMany({
      where: { hotelId: hotel.id, status: { in: ['VACANT_DIRTY', 'CLEANING', 'INSPECTION'] } },
      include: {
        stays: { where: { status: 'CHECKED_IN' }, include: { guest: true }, take: 1 },
      },
      orderBy: { number: 'asc' },
    }),
  ])

  return { hotel, tasks, rooms }
}

const TASK_TYPE_LABELS: Record<string, string> = {
  FULL_CLEAN: 'Full Clean',
  CHECKOUT_CLEAN: 'Checkout Clean',
  DAILY_CLEAN: 'Daily Clean',
  TURNDOWN: 'Turndown',
  TOWELS_ONLY: 'Towels Only',
  INSPECTION: 'Inspection',
  WELCOME_SETUP: 'Welcome Setup',
}

const INSTRUCTION_LABELS: Record<string, string> = {
  CLEAN_NOW: '🟢 Clean Now',
  CLEAN_LATER: '🕐 Clean Later',
  DND: '🔴 Do Not Disturb',
  TOWELS_ONLY: '🟡 Towels Only',
}

export default async function HousekeepingPage() {
  const data = await getData()
  if (!data) return null
  const { tasks, rooms } = data

  const pending = tasks.filter(t => t.status === 'PENDING')
  const inProgress = tasks.filter(t => t.status === 'IN_PROGRESS')
  const completed = tasks.filter(t => t.status === 'COMPLETED')

  const stats = {
    pending: pending.length,
    inProgress: inProgress.length,
    completed: completed.length,
    total: tasks.length,
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="section-title">Housekeeping</h1>
        <p className="section-subtitle">{stats.pending + stats.inProgress} tasks active · {stats.completed} completed</p>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Pending', value: stats.pending, color: 'bg-amber-50 text-amber-800 border border-amber-200' },
          { label: 'In Progress', value: stats.inProgress, color: 'bg-blue-50 text-blue-800 border border-blue-200' },
          { label: 'Completed Today', value: stats.completed, color: 'bg-emerald-50 text-emerald-800 border border-emerald-200' },
          { label: 'Rooms Needing Attention', value: rooms.length, color: 'bg-[#1E2761]/5 text-[#1E2761]' },
        ].map(s => (
          <div key={s.label} className="stat-card">
            <div className={cn('inline-flex items-center justify-center w-9 h-9 rounded-xl text-base font-bold mb-2', s.color)}>
              {s.value}
            </div>
            <div className="text-xs text-[#667085]">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Room status quick view */}
      {rooms.length > 0 && (
        <div className="data-card p-4">
          <h2 className="font-semibold text-sm text-[#182033] mb-3">Rooms Requiring Attention</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {rooms.map(room => (
              <div key={room.id} className={cn(
                'rounded-xl p-3 border text-sm',
                room.status === 'VACANT_DIRTY' ? 'bg-amber-50 border-amber-200' :
                room.status === 'CLEANING' ? 'bg-blue-50 border-blue-200' :
                'bg-purple-50 border-purple-200'
              )}>
                <div className="font-bold text-base">{room.number}</div>
                <div className="text-xs mt-0.5 text-[#667085]">{room.type} · Floor {room.floor}</div>
                <div className={cn('text-xs font-semibold mt-1',
                  room.status === 'VACANT_DIRTY' ? 'text-amber-700' :
                  room.status === 'CLEANING' ? 'text-blue-700' : 'text-purple-700'
                )}>
                  {room.status.replace('_', ' ')}
                </div>
                {room.stays[0] && (
                  <div className="text-[10px] text-[#667085] mt-1">
                    Was: {room.stays[0].guest.firstName} {room.stays[0].guest.lastName}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active tasks */}
      {[...pending, ...inProgress].length > 0 && (
        <div className="data-card overflow-hidden">
          <div className="px-4 py-3 border-b border-[#E4E8F1] bg-[#F5F7FB]">
            <span className="font-semibold text-sm text-[#182033]">Active Tasks</span>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#E4E8F1]">
                <th className="table-header">Room</th>
                <th className="table-header">Task</th>
                <th className="table-header">Guest Instruction</th>
                <th className="table-header">Assigned</th>
                <th className="table-header">Scheduled</th>
                <th className="table-header">Notes</th>
                <th className="table-header">Action</th>
              </tr>
            </thead>
            <tbody>
              {[...pending, ...inProgress].map(task => (
                <HousekeepingTaskRow key={task.id} task={task} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Completed tasks */}
      {completed.length > 0 && (
        <div className="data-card overflow-hidden">
          <div className="px-4 py-3 border-b border-[#E4E8F1] bg-[#F5F7FB]">
            <span className="font-semibold text-sm text-[#182033]">Completed</span>
          </div>
          <div className="divide-y divide-[#E4E8F1]">
            {completed.map(task => (
              <div key={task.id} className="px-4 py-3 flex items-center gap-4 opacity-60">
                <span className="badge bg-emerald-50 text-emerald-700 text-[10px]">✓ DONE</span>
                <span className="font-medium text-sm text-[#182033]">Room {task.room.number}</span>
                <span className="text-xs text-[#667085]">{TASK_TYPE_LABELS[task.type] || task.type}</span>
                {task.assignedTo && <span className="text-xs text-[#667085]">by {task.assignedTo}</span>}
                {task.completedAt && <span className="text-xs text-[#667085] ml-auto">{friendlyDate(task.completedAt)}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
