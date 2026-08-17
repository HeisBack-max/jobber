'use client'

import { useState } from 'react'
import { Wifi, Phone, Clock, MapPin, Star, MessageSquare, ChevronRight, X, Send, Coffee, Utensils, Beer, ShoppingBag, Pill, Smartphone, Shirt, Car, Landmark, Moon } from 'lucide-react'

const TRANSLATIONS = {
  en: {
    welcome: 'Welcome',
    to: 'to A Z Hotel',
    yourRoom: 'Your Room',
    checkOut: 'Check-out',
    wifi: 'WiFi',
    wifiPwd: 'Password',
    quickActions: 'Quick Actions',
    localGuide: 'Local Guide',
    localSub: 'Curated Phnom Penh picks',
    callFrontDesk: 'Call Front Desk',
    requestService: 'Request Service',
    feedback: 'Share Feedback',
    serviceReq: 'Service Request',
    serviceDesc: 'Describe what you need and we\'ll take care of it.',
    yourMessage: 'What do you need?',
    sendRequest: 'Send Request',
    cancel: 'Cancel',
    sending: 'Sending…',
    sent: 'Request sent! We\'ll be with you shortly.',
    checkIn: 'Check-in',
    checkInTime: 'After 2:00 PM',
    checkOutTime: 'Before 12:00 PM',
    hotline: '24h Hotline',
    lateCheckout: 'Late check-out? Ask us.',
    currency: 'Currency',
    currencyInfo: 'USD & KHR accepted. ATM on street.',
    emergency: 'Emergency',
    emergencyInfo: 'Police 117 · Ambulance 119',
    feedbackTitle: 'How\'s your stay?',
    feedbackSub: 'We read every response and act on it.',
    feedbackSent: 'Thank you! Your feedback means a lot.',
    feedbackQ: 'Tell us how we can make your stay better',
    rate: 'Rate your stay',
    submit: 'Submit',
    categories: {
      eat: 'Eat', coffee: 'Coffee', drinks: 'Drinks', essentials: 'Essentials',
      pharmacy: 'Pharmacy', sim: 'SIM Card', laundry: 'Laundry', transport: 'Transport',
      attractions: 'Attractions', late_night: 'Late Night', tips: 'Tips',
    },
  },
  km: {
    welcome: 'សូមស្វាគមន៍',
    to: 'មកកាន់សណ្ឋាគារ A Z',
    yourRoom: 'បន្ទប់របស់អ្នក',
    checkOut: 'ថ្ងៃចេញ',
    wifi: 'WiFi',
    wifiPwd: 'ពាក្យសម្ងាត់',
    quickActions: 'សកម្មភាពរហ័ស',
    localGuide: 'មគ្គុទ្ទេសក៍ក្នុងស្រុក',
    localSub: 'ទីកន្លែងល្អបំផុតក្នុងភ្នំពេញ',
    callFrontDesk: 'ទូរស័ព្ទទៅកន្លែងទទួលភ្ញៀវ',
    requestService: 'សំណើសេវាកម្ម',
    feedback: 'ចែករំលែកមតិ',
    serviceReq: 'សំណើសេវាកម្ម',
    serviceDesc: 'ប្រាប់យើងអ្វីដែលអ្នកត្រូវការ។',
    yourMessage: 'តើអ្នកត្រូវការអ្វី?',
    sendRequest: 'ផ្ញើសំណើ',
    cancel: 'បោះបង់',
    sending: 'កំពុងផ្ញើ…',
    sent: 'បានផ្ញើ! យើងនឹងចូលទៅជួយអ្នកភ្លាមៗ។',
    checkIn: 'ចូលស្នាក់',
    checkInTime: 'បន្ទាប់ពី 2:00 PM',
    checkOutTime: 'មុន 12:00 PM',
    hotline: 'ខ្សែទូរស័ព្ទ 24ម',
    lateCheckout: 'ចេញយឺត? សួរយើង។',
    currency: 'រូបិយប័ណ្ណ',
    currencyInfo: 'ទទួល USD & KHR · ATM នៅខាងក្រៅ',
    emergency: 'អាសន្ន',
    emergencyInfo: 'ប៉ូលិស 117 · មន្ទីរពេទ្យ 119',
    feedbackTitle: 'ការស្នាក់នៅប្រព្រឹត្តយ៉ាងណា?',
    feedbackSub: 'យើងអានរាល់ចម្លើយ។',
    feedbackSent: 'អរគុណ! មតិរបស់អ្នកមានន័យច្រើន។',
    feedbackQ: 'ប្រាប់យើងពីរបៀបធ្វើឱ្យការស្នាក់នៅប្រសើរជាងនេះ',
    rate: 'វាយតម្លៃការស្នាក់នៅ',
    submit: 'បញ្ជូន',
    categories: {
      eat: 'ញ៉ាំ', coffee: 'កាហ្វេ', drinks: 'ភេសជ្ជៈ', essentials: 'ចាំបាច់',
      pharmacy: 'ឱសថស្ថាន', sim: 'ស៊ីម', laundry: 'បោកខោអាវ', transport: 'ដឹកជញ្ជូន',
      attractions: 'កន្លែងទស្សនា', late_night: 'យប់ក្រោយ', tips: 'គន្លឹះ',
    },
  },
  zh: {
    welcome: '欢迎',
    to: '入住 A Z 酒店',
    yourRoom: '您的房间',
    checkOut: '退房日期',
    wifi: '无线网络',
    wifiPwd: '密码',
    quickActions: '快捷操作',
    localGuide: '本地指南',
    localSub: '精选金边好去处',
    callFrontDesk: '联系前台',
    requestService: '服务请求',
    feedback: '分享反馈',
    serviceReq: '服务请求',
    serviceDesc: '告诉我们您需要什么，我们会立即处理。',
    yourMessage: '您需要什么？',
    sendRequest: '发送请求',
    cancel: '取消',
    sending: '发送中…',
    sent: '请求已发送！我们很快会来为您服务。',
    checkIn: '入住',
    checkInTime: '下午 2:00 后',
    checkOutTime: '中午 12:00 前',
    hotline: '24小时热线',
    lateCheckout: '延迟退房？请联系我们。',
    currency: '货币',
    currencyInfo: '接受美元和瑞尔 · 附近有ATM',
    emergency: '紧急情况',
    emergencyInfo: '警察 117 · 救护车 119',
    feedbackTitle: '您的住宿体验如何？',
    feedbackSub: '我们认真阅读每一条反馈。',
    feedbackSent: '感谢您的反馈！',
    feedbackQ: '请告诉我们如何改善您的住宿体验',
    rate: '评分',
    submit: '提交',
    categories: {
      eat: '餐厅', coffee: '咖啡', drinks: '酒吧', essentials: '便利',
      pharmacy: '药店', sim: 'SIM卡', laundry: '洗衣', transport: '交通',
      attractions: '景点', late_night: '深夜', tips: '小贴士',
    },
  },
}

const CATEGORY_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  eat: Utensils, coffee: Coffee, drinks: Beer, essentials: ShoppingBag,
  pharmacy: Pill, sim: Smartphone, laundry: Shirt, transport: Car,
  attractions: Landmark, late_night: Moon,
}

type Recommendation = {
  id: string; category: string; name: string; description: string | null
  distance: string | null; hours: string | null; priceRange: string | null
  hotelNote: string | null
}

type Lang = 'en' | 'km' | 'zh'

type Props = {
  hotelName: string; wifiName: string; wifiPassword: string
  checkInTime: string; checkOutTime: string; phone: string
  guestFirstName: string | null; roomNumber: string | null
  checkOutDate: string | null; stayToken: string | null
  recommendations: Recommendation[]
  lang: Lang
}

export default function GuestCompanionClient({
  hotelName, wifiName, wifiPassword, checkInTime, checkOutTime, phone,
  guestFirstName, roomNumber, checkOutDate, stayToken, recommendations, lang,
}: Props) {
  const t = TRANSLATIONS[lang] || TRANSLATIONS.en
  const [activeTab, setActiveTab] = useState<'home' | 'local' | 'info'>('home')
  const [showServiceModal, setShowServiceModal] = useState(false)
  const [showFeedbackModal, setShowFeedbackModal] = useState(false)
  const [serviceMessage, setServiceMessage] = useState('')
  const [serviceStatus, setServiceStatus] = useState<'idle' | 'sending' | 'sent'>('idle')
  const [feedbackRating, setFeedbackRating] = useState(0)
  const [feedbackComment, setFeedbackComment] = useState('')
  const [feedbackStatus, setFeedbackStatus] = useState<'idle' | 'sending' | 'sent'>('idle')
  const [activeCat, setActiveCat] = useState<string | null>(null)

  const sendServiceRequest = async () => {
    if (!serviceMessage.trim()) return
    setServiceStatus('sending')
    try {
      await fetch('/api/requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'GUEST_REQUEST',
          category: 'room',
          description: serviceMessage,
          priority: 'NORMAL',
          token: stayToken,
        }),
      })
      setServiceStatus('sent')
      setTimeout(() => { setShowServiceModal(false); setServiceStatus('idle'); setServiceMessage('') }, 2000)
    } catch {
      setServiceStatus('idle')
    }
  }

  const sendFeedback = async () => {
    if (!feedbackRating && !feedbackComment.trim()) return
    setFeedbackStatus('sending')
    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating: feedbackRating, comment: feedbackComment, token: stayToken }),
      })
      setFeedbackStatus('sent')
      setTimeout(() => { setShowFeedbackModal(false); setFeedbackStatus('idle'); setFeedbackRating(0); setFeedbackComment('') }, 2000)
    } catch {
      setFeedbackStatus('idle')
    }
  }

  const byCategory = recommendations.reduce((acc, r) => {
    if (!acc[r.category]) acc[r.category] = []
    acc[r.category].push(r)
    return acc
  }, {} as Record<string, Recommendation[]>)

  const categories = Object.keys(byCategory)
  const filteredRecs = activeCat ? byCategory[activeCat] || [] : recommendations

  return (
    <div className="min-h-screen bg-[#F5F7FB] flex flex-col" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>

      {/* Header */}
      <header className="bg-[#1E2761] text-white">
        <div className="px-4 pt-12 pb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#C9A84C] flex items-center justify-center text-[#121A45] font-bold text-sm">AZ</div>
              <div>
                <div className="text-xs text-[#CADCFC] font-medium">{hotelName}</div>
                <div className="text-[10px] text-[#CADCFC]/60">Guest Companion</div>
              </div>
            </div>
            <div className="flex gap-1">
              {(['en', 'km', 'zh'] as const).map(l => (
                <a key={l} href={`?${stayToken ? `token=${stayToken}&` : ''}lang=${l}`}
                  className={`text-xs px-2 py-1 rounded-full ${lang === l ? 'bg-[#C9A84C] text-[#121A45] font-semibold' : 'text-[#CADCFC] bg-white/10'}`}>
                  {l === 'en' ? 'EN' : l === 'km' ? 'ខ្មែរ' : '中'}
                </a>
              ))}
            </div>
          </div>

          {guestFirstName ? (
            <div>
              <div className="text-2xl font-bold">{t.welcome}, {guestFirstName}</div>
              {roomNumber && <div className="text-[#CADCFC] mt-1">{t.yourRoom} <span className="font-bold text-white">{roomNumber}</span></div>}
              {checkOutDate && <div className="text-[#CADCFC]/70 text-xs mt-0.5">{t.checkOut}: {checkOutDate}</div>}
            </div>
          ) : (
            <div>
              <div className="text-2xl font-bold">{t.welcome}</div>
              <div className="text-[#CADCFC]">{t.to}</div>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex border-t border-white/10">
          {[
            { id: 'home', label: '🏨 Home' },
            { id: 'local', label: '📍 Local' },
            { id: 'info', label: 'ℹ️ Info' },
          ].map(tab => (
            <button key={tab.id}
              onClick={() => setActiveTab(tab.id as 'home' | 'local' | 'info')}
              className={`flex-1 py-3 text-sm font-medium transition-colors ${activeTab === tab.id ? 'text-[#C9A84C] border-b-2 border-[#C9A84C]' : 'text-[#CADCFC]/70'}`}>
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 px-4 py-5 space-y-4 max-w-lg mx-auto w-full">

        {/* HOME TAB */}
        {activeTab === 'home' && (
          <>
            {/* WiFi card */}
            <div className="bg-white rounded-2xl p-4 shadow-sm border border-[#E4E8F1]">
              <div className="flex items-center gap-2 mb-3">
                <Wifi className="w-4 h-4 text-[#1E2761]" />
                <span className="font-semibold text-[#182033]">{t.wifi}</span>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#667085]">Network</span>
                  <span className="font-mono text-sm font-semibold text-[#182033]">{wifiName}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#667085]">{t.wifiPwd}</span>
                  <span className="font-mono text-sm font-semibold text-[#1E2761]">{wifiPassword}</span>
                </div>
              </div>
            </div>

            {/* Quick actions */}
            <div>
              <div className="text-xs font-semibold text-[#667085] uppercase tracking-wide mb-2">{t.quickActions}</div>
              <div className="grid grid-cols-2 gap-3">
                <button onClick={() => setShowServiceModal(true)}
                  className="bg-[#1E2761] text-white rounded-2xl p-4 flex flex-col items-start gap-2 active:opacity-90">
                  <MessageSquare className="w-5 h-5 text-[#C9A84C]" />
                  <span className="font-semibold text-sm">{t.requestService}</span>
                  <span className="text-xs text-[#CADCFC]/70">Towels, pillows, F&amp;B…</span>
                </button>
                <button onClick={() => setShowFeedbackModal(true)}
                  className="bg-white border border-[#E4E8F1] rounded-2xl p-4 flex flex-col items-start gap-2 active:opacity-90">
                  <Star className="w-5 h-5 text-[#C9A84C]" />
                  <span className="font-semibold text-sm text-[#182033]">{t.feedback}</span>
                  <span className="text-xs text-[#667085]">Tell us how it's going</span>
                </button>
                <button onClick={() => phone && (window.location.href = `tel:${phone}`)}
                  className="bg-white border border-[#E4E8F1] rounded-2xl p-4 flex flex-col items-start gap-2 active:opacity-90">
                  <Phone className="w-5 h-5 text-[#1E2761]" />
                  <span className="font-semibold text-sm text-[#182033]">{t.callFrontDesk}</span>
                  <span className="text-xs text-[#667085]">{t.hotline}</span>
                </button>
                <button onClick={() => setActiveTab('local')}
                  className="bg-white border border-[#E4E8F1] rounded-2xl p-4 flex flex-col items-start gap-2 active:opacity-90">
                  <MapPin className="w-5 h-5 text-[#1E2761]" />
                  <span className="font-semibold text-sm text-[#182033]">{t.localGuide}</span>
                  <span className="text-xs text-[#667085]">{t.localSub}</span>
                </button>
              </div>
            </div>

            {/* Times */}
            <div className="bg-white rounded-2xl p-4 shadow-sm border border-[#E4E8F1]">
              <div className="flex items-center gap-2 mb-3">
                <Clock className="w-4 h-4 text-[#1E2761]" />
                <span className="font-semibold text-[#182033] text-sm">Hotel Times</span>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#667085]">{t.checkIn}</span>
                  <span className="text-sm font-semibold text-[#182033]">{t.checkInTime}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#667085]">Check-out</span>
                  <span className="text-sm font-semibold text-[#182033]">{t.checkOutTime}</span>
                </div>
              </div>
              <div className="mt-3 text-xs text-[#C9A84C]">{t.lateCheckout}</div>
            </div>
          </>
        )}

        {/* LOCAL GUIDE TAB */}
        {activeTab === 'local' && (
          <>
            <div className="text-xs font-semibold text-[#667085] uppercase tracking-wide">{t.localGuide}</div>

            {/* Category filter */}
            <div className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4">
              <button onClick={() => setActiveCat(null)}
                className={`flex-shrink-0 text-xs px-3 py-1.5 rounded-full border transition-colors ${!activeCat ? 'bg-[#1E2761] text-white border-[#1E2761]' : 'bg-white border-[#E4E8F1] text-[#182033]'}`}>
                All
              </button>
              {categories.map(cat => {
                const Icon = CATEGORY_ICONS[cat]
                return (
                  <button key={cat} onClick={() => setActiveCat(cat === activeCat ? null : cat)}
                    className={`flex-shrink-0 flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-colors ${activeCat === cat ? 'bg-[#1E2761] text-white border-[#1E2761]' : 'bg-white border-[#E4E8F1] text-[#182033]'}`}>
                    {Icon && <Icon className="w-3 h-3" />}
                    {(t.categories as Record<string, string>)[cat] || cat}
                  </button>
                )
              })}
            </div>

            {/* Recommendations */}
            <div className="space-y-3">
              {filteredRecs.map(rec => (
                <div key={rec.id} className="bg-white rounded-2xl p-4 shadow-sm border border-[#E4E8F1]">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="font-semibold text-[#182033]">{rec.name}</span>
                    {rec.priceRange && (
                      <span className="text-xs text-[#667085] bg-gray-50 px-1.5 py-0.5 rounded flex-shrink-0">{rec.priceRange}</span>
                    )}
                  </div>
                  {rec.description && (
                    <p className="text-xs text-[#667085] leading-relaxed mb-2">{rec.description}</p>
                  )}
                  <div className="space-y-1">
                    {rec.distance && (
                      <div className="text-xs text-[#667085] flex items-center gap-1">
                        <MapPin className="w-3 h-3" /> {rec.distance}
                      </div>
                    )}
                    {rec.hours && (
                      <div className="text-xs text-[#667085] flex items-center gap-1">
                        <Clock className="w-3 h-3" /> {rec.hours}
                      </div>
                    )}
                  </div>
                  {rec.hotelNote && (
                    <div className="mt-2 bg-[#FFF8E7] border border-[#C9A84C]/20 rounded-lg p-2 text-xs text-[#A66E00]">
                      <span className="font-semibold">A Z recommends:</span> {rec.hotelNote}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}

        {/* INFO TAB */}
        {activeTab === 'info' && (
          <>
            <div className="text-xs font-semibold text-[#667085] uppercase tracking-wide">Hotel Info</div>
            <div className="space-y-3">
              {[
                { icon: '💵', label: t.currency, value: t.currencyInfo },
                { icon: '🚨', label: t.emergency, value: t.emergencyInfo },
                { icon: '🕐', label: 'Check-in', value: `After ${checkInTime}` },
                { icon: '🚪', label: 'Check-out', value: `Before ${checkOutTime}` },
                { icon: '🍳', label: 'Breakfast', value: '7:00 – 10:30 AM · Restaurant, Ground Floor' },
                { icon: '🧹', label: 'Housekeeping', value: 'Daily 9:00 AM – 4:00 PM · DND cards available' },
                { icon: '🏧', label: 'ATM', value: '50m · Street 19, beside 7-Eleven' },
                { icon: '🚗', label: 'Airport Transfer', value: 'Ask front desk · $15 USD fixed rate' },
                { icon: '🛫', label: 'Airport', value: 'Phnom Penh International · 30 min by tuk-tuk' },
              ].map(item => (
                <div key={item.label} className="bg-white rounded-2xl px-4 py-3 flex items-start gap-3 shadow-sm border border-[#E4E8F1]">
                  <span className="text-lg">{item.icon}</span>
                  <div>
                    <div className="font-semibold text-xs text-[#182033]">{item.label}</div>
                    <div className="text-xs text-[#667085]">{item.value}</div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </main>

      {/* Bottom bar */}
      <div className="sticky bottom-0 bg-white border-t border-[#E4E8F1] px-4 py-3 flex items-center justify-between max-w-lg mx-auto w-full">
        <div className="text-xs text-[#667085]">A Z Hotel · Phnom Penh</div>
        {phone && (
          <a href={`tel:${phone}`} className="text-xs bg-[#1E2761] text-white px-4 py-2 rounded-full font-semibold flex items-center gap-1.5">
            <Phone className="w-3 h-3" /> {t.callFrontDesk}
          </a>
        )}
      </div>

      {/* Service Request Modal */}
      {showServiceModal && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50" onClick={() => setShowServiceModal(false)}>
          <div className="bg-white rounded-t-3xl w-full p-6 max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg text-[#182033]">{t.serviceReq}</h3>
              <button onClick={() => setShowServiceModal(false)} className="text-[#667085]">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-[#667085] mb-4">{t.serviceDesc}</p>
            {serviceStatus === 'sent' ? (
              <div className="text-center py-8 text-emerald-600 font-semibold">{t.sent}</div>
            ) : (
              <>
                <div className="mb-3">
                  <div className="flex flex-wrap gap-2 mb-3">
                    {['Extra towels', 'Pillows', 'Water', 'Iron', 'Room clean', 'Toothbrush kit'].map(item => (
                      <button key={item}
                        onClick={() => setServiceMessage(prev => prev ? `${prev}, ${item}` : item)}
                        className="text-xs border border-[#E4E8F1] text-[#182033] px-3 py-1.5 rounded-full hover:border-[#1E2761] hover:text-[#1E2761] transition-colors">
                        {item}
                      </button>
                    ))}
                  </div>
                  <textarea
                    value={serviceMessage}
                    onChange={e => setServiceMessage(e.target.value)}
                    placeholder={t.yourMessage}
                    rows={3}
                    className="w-full border border-[#E4E8F1] rounded-xl p-3 text-sm text-[#182033] resize-none focus:outline-none focus:border-[#1E2761]"
                  />
                </div>
                <div className="flex gap-3">
                  <button onClick={sendServiceRequest} disabled={serviceStatus === 'sending' || !serviceMessage.trim()}
                    className="flex-1 bg-[#1E2761] text-white py-3 rounded-xl font-semibold text-sm disabled:opacity-50 flex items-center justify-center gap-2">
                    <Send className="w-4 h-4" />
                    {serviceStatus === 'sending' ? t.sending : t.sendRequest}
                  </button>
                  <button onClick={() => setShowServiceModal(false)}
                    className="px-4 border border-[#E4E8F1] text-[#667085] rounded-xl font-medium text-sm">
                    {t.cancel}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Feedback Modal */}
      {showFeedbackModal && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50" onClick={() => setShowFeedbackModal(false)}>
          <div className="bg-white rounded-t-3xl w-full p-6 max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg text-[#182033]">{t.feedbackTitle}</h3>
              <button onClick={() => setShowFeedbackModal(false)} className="text-[#667085]"><X className="w-5 h-5" /></button>
            </div>
            <p className="text-sm text-[#667085] mb-4">{t.feedbackSub}</p>
            {feedbackStatus === 'sent' ? (
              <div className="text-center py-8 text-emerald-600 font-semibold">{t.feedbackSent}</div>
            ) : (
              <>
                <div className="mb-4">
                  <div className="text-xs text-[#667085] mb-2">{t.rate}</div>
                  <div className="flex gap-2">
                    {[1, 2, 3, 4, 5].map(star => (
                      <button key={star} onClick={() => setFeedbackRating(star)}
                        className={`text-3xl transition-transform ${star <= feedbackRating ? 'text-[#C9A84C]' : 'text-gray-200'} hover:scale-110`}>
                        ★
                      </button>
                    ))}
                  </div>
                </div>
                <textarea
                  value={feedbackComment}
                  onChange={e => setFeedbackComment(e.target.value)}
                  placeholder={t.feedbackQ}
                  rows={3}
                  className="w-full border border-[#E4E8F1] rounded-xl p-3 text-sm text-[#182033] resize-none focus:outline-none focus:border-[#1E2761] mb-4"
                />
                <div className="flex gap-3">
                  <button onClick={sendFeedback} disabled={feedbackStatus === 'sending' || (!feedbackRating && !feedbackComment.trim())}
                    className="flex-1 bg-[#C9A84C] text-[#121A45] py-3 rounded-xl font-semibold text-sm disabled:opacity-50">
                    {feedbackStatus === 'sending' ? t.sending : t.submit}
                  </button>
                  <button onClick={() => setShowFeedbackModal(false)}
                    className="px-4 border border-[#E4E8F1] text-[#667085] rounded-xl font-medium text-sm">
                    {t.cancel}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
