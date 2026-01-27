import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Search, Bell, MessageSquare } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useSearchStore } from '@/store/searchStore'
import { useNotifications } from '@/context/NotificationContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { formatDistanceToNow } from 'date-fns'
import ru from 'date-fns/locale/ru'

export default function Header() {
  const { user } = useAuthStore()
  const { query, setQuery } = useSearchStore()
  const navigate = useNavigate()
  const [searchValue, setSearchValue] = useState(query)
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications()
  const [notificationsOpen, setNotificationsOpen] = useState(false)

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setQuery(searchValue)
    if (searchValue.trim()) {
      navigate(`/tasks?search=${encodeURIComponent(searchValue)}`)
    }
  }

  const getInitials = () => {
    if (user?.employee?.full_name_complete) {
      const parts = user.employee.full_name_complete.split(' ')
      if (parts.length >= 2) {
        return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
      }
      return parts[0][0].toUpperCase()
    }
    if (user?.employee?.full_name) {
      const parts = user.employee.full_name.split(' ')
      if (parts.length >= 2) {
        return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
      }
      return parts[0][0].toUpperCase()
    }
    return user?.username[0].toUpperCase() || 'U'
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between px-6">
        {/* Search */}
        <div className="flex-1 max-w-md">
          <form onSubmit={handleSearch} className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Поиск задач..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              className="w-full pl-10 pr-4"
            />
          </form>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon">
            <MessageSquare className="w-5 h-5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="relative"
            onClick={() => setNotificationsOpen(true)}
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <Badge
                variant="destructive"
                className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
              >
                {unreadCount > 9 ? '9+' : unreadCount}
              </Badge>
            )}
          </Button>

          {/* Notifications Dialog */}
          <Dialog open={notificationsOpen} onOpenChange={setNotificationsOpen}>
            <DialogContent className="max-h-[600px]" onClose={() => setNotificationsOpen(false)}>
              <DialogHeader>
                <DialogTitle>Уведомления</DialogTitle>
              </DialogHeader>
              <div className="space-y-2 mt-4">
                {unreadCount === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    Нет непрочитанных уведомлений
                  </p>
                ) : (
                  <>
                    {/* Показываем только непрочитанные уведомления (максимум 3) */}
                    {notifications
                      .filter((n) => !n.is_read)
                      .slice(0, 3)
                      .map((notification) => (
                        <div
                          key={notification.id}
                          className="p-3 rounded-lg border cursor-pointer hover:bg-accent transition-colors bg-accent/50 border-l-4 border-l-primary"
                          onClick={() => {
                            if (notification.url) {
                              markAsRead(notification.id)
                              // Исправляем URL - нормализуем формат
                              let url = notification.url.endsWith('/') 
                                ? notification.url.slice(0, -1) 
                                : notification.url
                              // Убеждаемся, что URL начинается с /
                              if (!url.startsWith('/')) {
                                url = '/' + url
                              }
                              // Исправляем старый формат /task/ на /tasks/
                              url = url.replace(/^\/task\//, '/tasks/')
                              console.log('Navigating to:', url)
                              navigate(url)
                              setNotificationsOpen(false)
                            }
                          }}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-primary flex-shrink-0" />
                                <p className="text-sm font-semibold">
                                  {notification.message}
                                </p>
                              </div>
                              <p className="text-xs text-muted-foreground mt-1">
                                {formatDistanceToNow(new Date(notification.created_at), {
                                  addSuffix: true,
                                  locale: ru,
                                })}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    {/* Показываем счетчик оставшихся непрочитанных, если их больше 3 */}
                    {unreadCount > 3 && (
                      <div className="pt-2 border-t">
                        <p className="text-sm text-muted-foreground text-center py-2">
                          И еще {unreadCount - 3} непрочитанных уведомлений
                        </p>
                      </div>
                    )}
                    {/* Кнопка "Посмотреть все" */}
                    <div className="pt-2 border-t">
                      <Button
                        variant="outline"
                        className="w-full"
                        onClick={() => {
                          setNotificationsOpen(false)
                          navigate('/notifications')
                        }}
                      >
                        Посмотреть все уведомления
                      </Button>
                    </div>
                  </>
                )}
              </div>
            </DialogContent>
          </Dialog>

          {/* User */}
          <Link
            to="/profile"
            className="flex items-center gap-3 hover:opacity-80 transition-opacity cursor-pointer"
          >
            <div className="text-right hidden md:block">
              <div className="text-sm font-medium">
                {user?.employee?.full_name_complete || user?.employee?.full_name || user?.username}
              </div>
              {user?.employee?.position && (
                <div className="text-xs text-muted-foreground">
                  {user.employee.position}
                </div>
              )}
            </div>
            {user?.employee?.photo_url ? (
              <img
                src={user.employee.photo_url}
                alt="Фото профиля"
                className="w-10 h-10 rounded-full object-cover border-2 border-primary"
              />
            ) : (
              <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white font-semibold">
                {getInitials()}
              </div>
            )}
          </Link>
        </div>
      </div>
    </header>
  )
}

