import { prisma } from '@/lib/db'
import { cn, SEVERITY_COLORS, ISSUE_STATUS_COLORS, friendlyDate } from '@/lib/utils'
import MaintenanceIssueRow from '@/components/maintenance/MaintenanceIssueRow'

export const dynamic = 'force-dynamic'
export const metadata = { title: 'Maintenance' }

async function getData() {
  const hotel = await prisma.hotel.findFirst({ where: { slug: 'az-hotel-phnom-penh' } })
  if (!hotel) return null

  const issues = await prisma.maintenanceIssue.findMany({
    where: { hotelId: hotel.id },
    include: { room: true },
    orderBy: [{ severity: 'desc' }, { status: 'asc' }, { createdAt: 'desc' }],
  })
  return { hotel, issues }
}

const CATEGORY_ICONS: Record<string, string> = {
  ac: '❄️', plumbing: '🚰', electrical: '⚡', wifi: '📶',
  furniture: '🪑', bathroom: '🚿', door: '🚪', lighting: '💡', other: '🔧',
}

const SEVERITY_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }

export default async function MaintenancePage() {
  const data = await getData()
  if (!data) return null
  const { issues } = data

  const openIssues = issues.filter(i => i.status !== 'RESOLVED' && i.status !== 'DEFERRED')
  const resolvedIssues = issues.filter(i => i.status === 'RESOLVED' || i.status === 'DEFERRED')

  const stats = {
    open: openIssues.filter(i => i.status === 'OPEN').length,
    inProgress: openIssues.filter(i => i.status === 'IN_PROGRESS').length,
    critical: issues.filter(i => i.severity === 'CRITICAL' && i.status !== 'RESOLVED').length,
    resolved: resolvedIssues.length,
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="section-title">Maintenance</h1>
        <p className="section-subtitle">{openIssues.length} open issues · {stats.resolved} resolved</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Critical', value: stats.critical, color: stats.critical > 0 ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-gray-50 text-gray-500' },
          { label: 'Open', value: stats.open, color: 'bg-amber-50 text-amber-800 border border-amber-200' },
          { label: 'In Progress', value: stats.inProgress, color: 'bg-blue-50 text-blue-800 border border-blue-200' },
          { label: 'Resolved', value: stats.resolved, color: 'bg-emerald-50 text-emerald-800' },
        ].map(s => (
          <div key={s.label} className="stat-card">
            <div className={cn('inline-flex items-center justify-center w-9 h-9 rounded-xl text-base font-bold mb-2', s.color)}>
              {s.value}
            </div>
            <div className="text-xs text-[#667085]">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Critical alert */}
      {stats.critical > 0 && (
        <div className="rounded-xl border border-red-300 bg-red-50 p-4 flex items-start gap-3">
          <span className="text-xl">⚠️</span>
          <div>
            <div className="font-semibold text-red-800">Critical maintenance requires immediate attention</div>
            <div className="text-sm text-red-700 mt-0.5">
              {openIssues.filter(i => i.severity === 'CRITICAL').map(i =>
                `Room ${i.room?.number || 'Hotel'}: ${i.description.slice(0, 60)}...`
              ).join(' · ')}
            </div>
          </div>
        </div>
      )}

      {/* Open issues */}
      {openIssues.length > 0 && (
        <div className="data-card overflow-hidden">
          <div className="px-4 py-3 border-b border-[#E4E8F1] bg-[#F5F7FB]">
            <span className="font-semibold text-sm text-[#182033]">Open Issues</span>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#E4E8F1]">
                <th className="table-header">Severity</th>
                <th className="table-header">Category</th>
                <th className="table-header">Description</th>
                <th className="table-header">Room</th>
                <th className="table-header">Reported</th>
                <th className="table-header">Assigned</th>
                <th className="table-header">Status</th>
                <th className="table-header">Action</th>
              </tr>
            </thead>
            <tbody>
              {openIssues.map(issue => (
                <MaintenanceIssueRow key={issue.id} issue={issue} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Resolved issues */}
      {resolvedIssues.length > 0 && (
        <div className="data-card overflow-hidden">
          <div className="px-4 py-3 border-b border-[#E4E8F1] bg-[#F5F7FB]">
            <span className="font-semibold text-sm text-[#182033]">Resolved</span>
          </div>
          <div className="divide-y divide-[#E4E8F1]">
            {resolvedIssues.map(issue => (
              <div key={issue.id} className="px-4 py-3 flex items-center gap-4 opacity-60">
                <span className="text-base">{CATEGORY_ICONS[issue.category] || '🔧'}</span>
                <span className="font-medium text-sm">{issue.category.toUpperCase()}</span>
                {issue.room && <span className="badge bg-gray-100 text-gray-500 text-[10px]">Room {issue.room.number}</span>}
                <span className="text-xs text-[#667085] flex-1">{issue.description.slice(0, 80)}</span>
                <span className="badge bg-emerald-50 text-emerald-700 text-[10px]">RESOLVED</span>
                {issue.resolvedAt && <span className="text-xs text-[#667085]">{friendlyDate(issue.resolvedAt)}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
