import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import api from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Bell, CheckCheck, Trash2, Check } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import ru from 'date-fns/locale/ru'
import { toast } from 'sonner'
import { Notification } from '@/types/task'

export default function Notifications() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Загрузка уведомлений
  const { data: notifications = [], isLoading } = useQuery<Notification[]>({
    queryKey: ['notifications'],
    queryFn: async () => {
      const response = await api.get('/notifications/')
      return response.data
    },
  })

  // Отметить как прочитанное
  const markReadMutation = useMutation({
    mutationFn: async (id: number) => {
      return api.post(`/notifications/${id}/read/`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  // Отметить все как прочитанные
  const markAllReadMutation = useMutation({
    mutationFn: async () => {
      return api.post('/notifications/mark-all-read/')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      toast.success('Все уведомления отмечены как прочитанные')
    },
  })

  // Удалить прочитанные
  const deleteReadMutation = useMutation({
    mutationFn: async () => {
      return api.delete('/notifications/delete-read/')
    },
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      toast.success(`Удалено ${response.data.deleted_count} прочитанных уведомлений`)
    },
  })

  const unreadCount = notifications.filter((n) => !n.is_read).length
  const readCount = notifications.filter((n) => n.is_read).length

  const handleNotificationClick = (notification: Notification) => {
    // Отмечаем как прочитанное при клике
    if (!notification.is_read) {
      markReadMutation.mutate(notification.id)
    }

    // Переходим по URL, если он есть
    if (notification.url) {
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
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Уведомления</h1>
          <p className="text-muted-foreground mt-1">
            {unreadCount > 0 ? (
              <>
                <Badge variant="destructive" className="mr-2">
                  {unreadCount} непрочитанных
                </Badge>
                {readCount > 0 && `${readCount} прочитанных`}
              </>
            ) : (
              readCount > 0 ? `${readCount} прочитанных` : 'Нет уведомлений'
            )}
          </p>
        </div>
        <div className="flex gap-2">
          {unreadCount > 0 && (
            <Button
              variant="outline"
              onClick={() => markAllReadMutation.mutate()}
              disabled={markAllReadMutation.isPending}
            >
              <CheckCheck className="w-4 h-4 mr-2" />
              Отметить все как прочитанные
            </Button>
          )}
          {readCount > 0 && (
            <Button
              variant="outline"
              onClick={() => deleteReadMutation.mutate()}
              disabled={deleteReadMutation.isPending}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Удалить прочитанные
            </Button>
          )}
        </div>
      </div>

      {notifications.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Bell className="w-16 h-16 text-muted-foreground mb-4" />
            <p className="text-lg text-muted-foreground">Нет уведомлений</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {notifications.map((notification) => (
            <Card
              key={notification.id}
              className={`cursor-pointer transition-all hover:shadow-md ${
                !notification.is_read
                  ? 'border-l-4 border-l-primary bg-accent/50'
                  : 'opacity-75'
              }`}
              onClick={() => handleNotificationClick(notification)}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      {!notification.is_read && (
                        <div className="w-2 h-2 rounded-full bg-primary" />
                      )}
                      <p
                        className={`text-sm font-medium ${
                          !notification.is_read ? 'font-semibold' : ''
                        }`}
                      >
                        {notification.message}
                      </p>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(notification.created_at), {
                        addSuffix: true,
                        locale: ru,
                      })}
                    </p>
                  </div>
                  {!notification.is_read && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        markReadMutation.mutate(notification.id)
                      }}
                      disabled={markReadMutation.isPending}
                    >
                      <Check className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
