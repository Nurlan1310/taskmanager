import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'

export default function Layout() {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div className="ml-64">
        <Header />
        <main className="container mx-auto px-6 py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

