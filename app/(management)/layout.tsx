import Sidebar from '@/components/layout/Sidebar'
import TopBar from '@/components/layout/TopBar'

export default function ManagementLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-[#F5F7FB]">
      <Sidebar />
      <div className="ml-56">
        <TopBar />
        <main className="p-6 max-w-screen-xl">
          {children}
        </main>
      </div>
    </div>
  )
}
