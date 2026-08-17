import { prisma } from '@/lib/db'
import { cn, PRIORITY_COLORS, STATUS_COLORS, friendlyDate, guestName } from '@/lib/utils'
import RequestRow from '@/components/requests/RequestRow'

export const dynamic = 'force-dynamic'
export const metadata = { title: 'Requests' }

async function getData() {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return null

  const requests = await prisma.serviceRequest.findMany({
    where: { hotelId: hotel.id },
    include: { room: true, guest: true },
    orderBy: [
      { status: 'asc' },
      { priority: 'desc' },
      { createdAt: 'desc' },
    ],
  })
  return { hotel, requests }
}

const PRIORITY_ORDER = { URGENT: 0, HIGH: 1, NORMAL: 2, LOW: 3 }
const STATUS_GROUPS = [
  { key: 'open', label: 'Open', statuses: ['NEW', 'ACCEPTED', 'IN_PROGRESS', 'WAITING', 'ESCALATED'] },
  { key: 'closed', label: 'Completed', statuses: ['COMPLETED', 'CANCELLED'] },
]

export default async function RequestsPage() {
  const data = await getData()
  if (!data) return null
  const { requests } = data

  const openRequests = requests.filter(r => !['COMPLETED', 'CANCELLED'].includes(r.status))
  const closedRequests = requests.filter(r => ['COMPLETED', 'CANCELLED'].includes(r.status))

  const sortedOpen = [...openRequests].sort((a, b) =>
    (PRIORITY_ORDER[a.priority as keyof typeof PRIORITY_ORDER] ?? 99) -
    (PRIORITY_ORDER[b.priority as keyof typeof PRIORITY_ORDER] ?? 99)
  )

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="section-title">Service Requests</h1>
          <p className="section-subtitle">{openRequests.length} open · {closedRequests.length} completed today</p>
        </div>
        <div className="flex gap-2">
          {openRequests.filter(r => r.priority === 'HIGH').length > 0 && (
            <span className="badge bg-amber-50 text-amber-800 border border-amber-200">
              {openRequests.filter(r => r.priority === 'HIGH').length} high priority
            </span>
          )}
        </div>
      </div>

      {/* Open requests */}
      {sortedOpen.length > 0 ? (
        <div className="data-card overflow-hidden">
          <div className="px-4 py-3 border-b border-[#E4E8F1] bg-[#F5F7FB]">
            <span className="font-semibold text-sm text-[#182033]">Open Requests</span>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#E4E8F1]">
                <th className="table-header">Priority</th>
                <th className="table-header">Category</th>
                <th className="table-header">Description</th>
                <th className="table-header">Room</th>
                <th className="table-header">Received</th>
                <th className="table-header">Status</th>
                <th className="table-header">Action</th>
              </tr>
            </thead>
            <tbody>
              {sortedOpen.map(req => (
                <RequestRow key={req.id} request={req} />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="data-card p-10 text-center text-[#667085]">
          <div className="text-3xl mb-2">✓</div>
          <p className="font-medium">All requests handled</p>
          <p className="text-sm">No open service requests at the moment.</p>
        </div>
      )}

      {/* Completed requests */}
      {closedRequests.length > 0 && (
        <div className="data-card overflow-hidden">
          <div className="px-4 py-3 border-b border-[#E4E8F1] bg-[#F5F7FB]">
            <span className="font-semibold text-sm text-[#182033]">Completed</span>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#E4E8F1]">
                <th className="table-header">Category</th>
                <th className="table-header">Description</th>
                <th className="table-header">Room</th>
                <th className="table-header">Received</th>
                <th className="table-header">Status</th>
                <th className="table-header">Assigned</th>
              </tr>
            </thead>
            <tbody>
              {closedRequests.map(req => (
                <tr key={req.id} className="opacity-60 hover:opacity-80 transition-opacity">
                  <td className="table-cell">
                    <span className="text-sm font-medium text-[#182033]">{req.category}</span>
                  </td>
                  <td className="table-cell text-[#667085] max-w-xs">
                    <span className="line-clamp-1">{req.description}</span>
                  </td>
                  <td className="table-cell">
                    {req.room && <span className="badge bg-[#1E2761]/5 text-[#1E2761]">Room {req.room.number}</span>}
                  </td>
                  <td className="table-cell text-[#667085] text-xs">{friendlyDate(req.createdAt)}</td>
                  <td className="table-cell">
                    <span className={cn('badge text-[10px]', STATUS_COLORS[req.status])}>{req.status}</span>
                  </td>
                  <td className="table-cell text-xs text-[#667085]">{req.assignedTo || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
