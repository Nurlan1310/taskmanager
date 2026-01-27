import { Link, useLocation, useNavigate } from 'react-router-dom'
import { 
  LayoutDashboard, 
  CheckSquare, 
  Calendar, 
  Users, 
  UserCheck,
  Settings,
  LogOut,
  Archive,
  UserCircle,
  ClipboardList,
  BarChart3,
  Bell
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useNotifications } from '@/context/NotificationContext'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

const menuItems = [
  { icon: LayoutDashboard, label: 'Дашборд', path: '/' },
  { icon: CheckSquare, label: 'Задачи', path: '/tasks' },
  { icon: ClipboardList, label: 'Поручения', path: '/assignments' },
  { icon: Calendar, label: 'Календарь', path: '/calendar' },
  { icon: Calendar, label: 'Мероприятия', path: '/cards' },
  { icon: Archive, label: 'Архив', path: '/archive' },
  { icon: BarChart3, label: 'Статистика', path: '/statistics' },
  { icon: Users, label: 'Сотрудники', path: '/employees' },
  { icon: UserCheck, label: 'Замещение', path: '/delegation' },
  { icon: Bell, label: 'Уведомления', path: '/notifications' },
]

export default function Sidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { logout } = useAuthStore()
  const { unreadCount } = useNotifications()
  
  const handleLogout = async () => {
    try {
      await logout()
      navigate('/login')
    } catch (error) {
      console.error('Logout error:', error)
      // В любом случае перенаправляем на логин
      navigate('/login')
    }
  }

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-slate-900 text-white flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
            <CheckSquare className="w-6 h-6" />
          </div>
          <h1 className="text-xl font-bold">TaskManager</h1>
        </div>
      </div>

      {/* Menu */}
      <nav className="flex-1 p-4 space-y-2">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 mb-4">
          Меню
        </div>
        {menuItems.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.path
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors",
                isActive
                  ? "bg-primary text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              )}
            >
              <Icon className="w-5 h-5" />
              <span>{item.label}</span>
              {item.path === '/notifications' && unreadCount > 0 && (
                <Badge variant="destructive" className="ml-auto">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </Badge>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Settings & Logout */}
      <div className="p-4 border-t border-slate-800 space-y-2">
        <Link
          to="/profile"
          className={cn(
            "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors",
            location.pathname === '/profile'
              ? "bg-primary text-white"
              : "text-slate-300 hover:bg-slate-800 hover:text-white"
          )}
        >
          <UserCircle className="w-5 h-5" />
          <span>Профиль</span>
        </Link>
        <Link
          to="/settings"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
        >
          <Settings className="w-5 h-5" />
          <span>Настройки</span>
        </Link>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
        >
          <LogOut className="w-5 h-5" />
          <span>Выйти</span>
        </button>
      </div>
    </aside>
  )
}

