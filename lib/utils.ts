import { type ClassValue, clsx } from 'clsx'
import { format, formatDistanceToNow, isToday, isTomorrow, isYesterday } from 'date-fns'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function formatDate(date: Date | string, fmt = 'dd MMM yyyy') {
  return format(new Date(date), fmt)
}

export function formatTime(date: Date | string) {
  return format(new Date(date), 'HH:mm')
}

export function formatDateTime(date: Date | string) {
  return format(new Date(date), 'dd MMM · HH:mm')
}

export function timeAgo(date: Date | string) {
  return formatDistanceToNow(new Date(date), { addSuffix: true })
}

export function friendlyDate(date: Date | string) {
  const d = new Date(date)
  if (isToday(d)) return `Today, ${format(d, 'HH:mm')}`
  if (isTomorrow(d)) return `Tomorrow, ${format(d, 'HH:mm')}`
  if (isYesterday(d)) return `Yesterday, ${format(d, 'HH:mm')}`
  return format(d, 'EEE dd MMM')
}

export function nightsCount(checkIn: Date | string, checkOut: Date | string) {
  const ms = new Date(checkOut).getTime() - new Date(checkIn).getTime()
  return Math.round(ms / (1000 * 60 * 60 * 24))
}

export function guestName(guest: { firstName: string; lastName: string }) {
  return `${guest.firstName} ${guest.lastName}`
}

export const ROOM_STATUS_LABELS: Record<string, string> = {
  OCCUPIED: 'Occupied',
  VACANT_CLEAN: 'Vacant — Clean',
  VACANT_DIRTY: 'Vacant — Dirty',
  CLEANING: 'Cleaning',
  INSPECTION: 'Inspection',
  MAINTENANCE: 'Maintenance',
  OUT_OF_SERVICE: 'Out of Service',
}

export const ROOM_STATUS_COLORS: Record<string, string> = {
  OCCUPIED: 'bg-navy text-white',
  VACANT_CLEAN: 'bg-emerald-100 text-emerald-800 border border-emerald-200',
  VACANT_DIRTY: 'bg-amber-100 text-amber-800 border border-amber-200',
  CLEANING: 'bg-blue-100 text-blue-800 border border-blue-200',
  INSPECTION: 'bg-purple-100 text-purple-800 border border-purple-200',
  MAINTENANCE: 'bg-orange-100 text-orange-800 border border-orange-200',
  OUT_OF_SERVICE: 'bg-gray-200 text-gray-500 border border-gray-300',
}

export const PRIORITY_COLORS: Record<string, string> = {
  LOW: 'bg-gray-100 text-gray-600',
  NORMAL: 'bg-blue-50 text-blue-700',
  HIGH: 'bg-amber-50 text-amber-800 border border-amber-200',
  URGENT: 'bg-red-50 text-red-700 border border-red-200',
}

export const STATUS_COLORS: Record<string, string> = {
  NEW: 'bg-blue-50 text-blue-700 border border-blue-200',
  ACCEPTED: 'bg-indigo-50 text-indigo-700',
  IN_PROGRESS: 'bg-amber-50 text-amber-800 border border-amber-200',
  WAITING: 'bg-gray-100 text-gray-600',
  COMPLETED: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  ESCALATED: 'bg-red-50 text-red-700 border border-red-200',
  CANCELLED: 'bg-gray-100 text-gray-400',
}

export const SEVERITY_COLORS: Record<string, string> = {
  LOW: 'bg-gray-100 text-gray-600',
  MEDIUM: 'bg-amber-50 text-amber-800',
  HIGH: 'bg-orange-50 text-orange-800 border border-orange-200',
  CRITICAL: 'bg-red-50 text-red-700 border border-red-200',
}

export const ISSUE_STATUS_COLORS: Record<string, string> = {
  OPEN: 'bg-red-50 text-red-700 border border-red-200',
  IN_PROGRESS: 'bg-amber-50 text-amber-800',
  RESOLVED: 'bg-emerald-50 text-emerald-700',
  DEFERRED: 'bg-gray-100 text-gray-500',
}

export const CATEGORY_ICONS: Record<string, string> = {
  eat: '🍽️',
  coffee: '☕',
  drinks: '🍹',
  essentials: '🛒',
  pharmacy: '💊',
  sim: '📱',
  laundry: '👕',
  transport: '🛺',
  attractions: '🏛️',
  late_night: '🌙',
  tips: '💡',
}

export const CATEGORY_LABELS: Record<string, string> = {
  eat: 'Eat',
  coffee: 'Coffee',
  drinks: 'Drinks',
  essentials: 'Essentials',
  pharmacy: 'Pharmacy',
  sim: 'SIM & Phone',
  laundry: 'Laundry',
  transport: 'Transport',
  attractions: 'Attractions',
  late_night: 'Late Night',
  tips: 'Local Tips',
}
