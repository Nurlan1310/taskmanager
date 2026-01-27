import { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useBrowserNotifications } from '@/hooks/useBrowserNotifications'
import { Notification } from '@/types/task'
import { toast } from 'sonner'
import { useQueryClient, useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

interface NotificationContextType {
  notifications: Notification[]
  unreadCount: number
  markAsRead: (id: number) => void
  markAllAsRead: () => void
  addNotification: (notification: Notification) => void
  clearNotifications: () => void
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined)

export function NotificationProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const { showNotification: showBrowserNotification, hasPermission } = useBrowserNotifications()
  
  // Загружаем уведомления из API
  const { data: apiNotifications = [] } = useQuery<Notification[]>({
    queryKey: ['notifications'],
    queryFn: async () => {
      const response = await api.get('/notifications/')
      return response.data
    },
    refetchInterval: 10000, // Обновляем каждые 10 секунд для более быстрой синхронизации
  })
  
  const [notifications, setNotifications] = useState<Notification[]>([])
  
  // Умная синхронизация: объединяем API данные с локальными WebSocket уведомлениями
  useEffect(() => {
    if (apiNotifications && apiNotifications.length > 0) {
      // Умное объединение: приоритет у API, но сохраняем новые WebSocket уведомления
      setNotifications((prev) => {
        const apiIds = new Set(apiNotifications.map(n => n.id))
        // Находим локальные уведомления, которых еще нет в API (новые WebSocket)
        const localOnly = prev.filter(n => !apiIds.has(n.id))
        
        // Объединяем: сначала API (свежие данные), потом локальные (новые WebSocket)
        const merged = [...apiNotifications, ...localOnly]
        
        // Сортируем по дате создания (новые сверху)
        return merged.sort((a, b) => 
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
      })
    } else if (apiNotifications && apiNotifications.length === 0) {
      // Если API вернул пустой массив, сохраняем только локальные (не перезаписываем)
      // Это позволяет сохранить новые WebSocket уведомления до следующего обновления
    }
  }, [apiNotifications])

  const handleWebSocketMessage = useCallback((message: any) => {
    // Логирование для отладки
    console.log('NotificationContext received message:', message)
    
    // Обрабатываем только уведомления
    if (message.type === 'notification' && message.data) {
      const data = message.data
      console.log('Processing notification data:', data)
      const notification: Notification = {
        id: data.id,
        message: data.message || 'Новое уведомление',
        url: data.url,
        type: data.type,
        task_id: data.task_id,
        created_at: data.created_at || new Date().toISOString(),
        is_read: false,
      }

      // Добавляем уведомление в список, избегая дубликатов
      setNotifications((prev) => {
        // Проверяем, нет ли уже такого уведомления
        if (prev.some(n => n.id === notification.id)) {
          console.log('Notification already exists, skipping:', notification.id)
          return prev
        }
        
        // Добавляем новое уведомление в начало списка
        return [notification, ...prev]
      })

      // Показываем toast-уведомление
      const getToastTitle = (type?: string) => {
        switch (type) {
          case 'task.created':
            return 'Новая задача'
          case 'task.assigned':
            return 'Задача назначена'
          case 'task.status_changed':
            return 'Статус изменен'
          case 'task.comment_added':
            return 'Новый комментарий'
          case 'task.recalled':
            return 'Задача отозвана'
          case 'task.approved':
            return 'Задача согласована'
          case 'task.approval_required':
            return 'Требуется согласование'
          case 'task.review_taken':
            return 'Исполнение принято на проверку'
          case 'task.execution_sent_for_review':
            return 'Исполнение на проверке'
          case 'task.plan_approval_required':
            return 'Требуется согласование плана'
          case 'task.redirected':
            return 'Задача перенаправлена'
          case 'task.creation_rejected':
            return 'Создание поручения отклонено'
          case 'task.plan_approved':
            return 'План мероприятия утвержден'
          case 'task.plan_rejected':
            return 'План мероприятия отклонен'
          default:
            return 'Уведомление'
        }
      }

      // Функция для нормализации URL
      const normalizeUrl = (url: string): string => {
        let normalized = url.endsWith('/') ? url.slice(0, -1) : url
        if (!normalized.startsWith('/')) {
          normalized = '/' + normalized
        }
        normalized = normalized.replace(/^\/task\//, '/tasks/')
        return normalized
      }

      // Показываем toast-уведомление
      toast.info(getToastTitle(notification.type), {
        description: notification.message,
        action: notification.url
          ? {
              label: 'Открыть',
              onClick: () => {
                const url = normalizeUrl(notification.url!)
                window.location.href = url
              },
            }
          : undefined,
        duration: 5000,
      })

      // Показываем системное уведомление браузера (если разрешено)
      // Показываем только если вкладка не активна (document.hidden) или всегда (по желанию)
      if (hasPermission && notification.url) {
        const url = normalizeUrl(notification.url)
        // Показываем системное уведомление всегда, но можно изменить на:
        // if (document.hidden) { ... } - чтобы показывать только когда вкладка неактивна
        showBrowserNotification(
          {
            title: getToastTitle(notification.type),
            body: notification.message,
            icon: '/favicon.ico', // Браузер проигнорирует, если файла нет
            tag: `task-${notification.id}`, // Уникальный тег для каждого уведомления
            data: { url, taskId: notification.task_id },
            requireInteraction: false,
          },
          () => {
            // Обработчик клика по уведомлению
            window.location.href = url
          }
        )
      }

      // Инвалидируем кэш задач для обновления списка
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      // НЕ инвалидируем notifications сразу, чтобы не потерять новое уведомление
      // Вместо этого полагаемся на refetchInterval
    }
  }, [queryClient])

  const { isConnected } = useWebSocket({
    onMessage: handleWebSocketMessage,
    onConnect: () => {
      console.log('WebSocket connected for notifications')
    },
    onDisconnect: () => {
      console.log('WebSocket disconnected for notifications')
    },
  })
  
  // Логируем статус соединения для отладки
  useEffect(() => {
    if (!isConnected) {
      console.warn('WebSocket is not connected. Notifications may be delayed.')
    }
  }, [isConnected])

  const addNotification = useCallback((notification: Notification) => {
    setNotifications((prev) => [notification, ...prev])
  }, [])

  const markAsRead = useCallback((id: number) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
    )
    // Синхронизируем с сервером
    api.post(`/notifications/${id}/read/`).catch(console.error)
  }, [])

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
    // Синхронизируем с сервером
    api.post('/notifications/mark-all-read/').catch(console.error)
  }, [])

  const clearNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  const unreadCount = notifications.filter((n) => !n.is_read).length

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        markAsRead,
        markAllAsRead,
        addNotification,
        clearNotifications,
      }}
    >
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotifications() {
  const context = useContext(NotificationContext)
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider')
  }
  return context
}