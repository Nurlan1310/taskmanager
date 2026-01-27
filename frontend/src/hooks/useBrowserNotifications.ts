import { useEffect, useRef, useCallback } from 'react'

interface NotificationOptions {
  title: string
  body: string
  icon?: string
  badge?: string
  tag?: string
  data?: any
  requireInteraction?: boolean
}

/**
 * Хук для работы с системными уведомлениями браузера
 */
export function useBrowserNotifications() {
  const permissionRef = useRef<NotificationPermission>('default')
  const notificationRef = useRef<Notification | null>(null)

  // Проверяем поддержку уведомлений
  const isSupported = typeof window !== 'undefined' && 'Notification' in window

  // Запрашиваем разрешение при инициализации
  useEffect(() => {
    if (!isSupported) {
      console.warn('Browser notifications are not supported')
      return
    }

    // Проверяем текущий статус разрешения
    permissionRef.current = Notification.permission

    // Если разрешение еще не запрашивалось, запрашиваем его
    if (Notification.permission === 'default') {
      Notification.requestPermission().then((permission) => {
        permissionRef.current = permission
        if (permission === 'granted') {
          console.log('Browser notifications permission granted')
        } else {
          console.log('Browser notifications permission denied')
        }
      })
    }
  }, [isSupported])

  /**
   * Показывает системное уведомление
   */
  const showNotification = useCallback(
    (options: NotificationOptions, onClick?: () => void) => {
      if (!isSupported) {
        console.warn('Browser notifications are not supported')
        return
      }

      if (Notification.permission !== 'granted') {
        console.warn('Browser notifications permission not granted')
        // Пытаемся запросить разрешение снова
        Notification.requestPermission().then((permission) => {
          permissionRef.current = permission
          if (permission === 'granted') {
            // Повторяем попытку после получения разрешения
            showNotification(options, onClick)
          }
        })
        return
      }

      // Закрываем предыдущее уведомление, если оно есть
      if (notificationRef.current) {
        notificationRef.current.close()
      }

      // Создаем новое уведомление
      const notification = new Notification(options.title, {
        body: options.body,
        icon: options.icon || '/favicon.ico', // Иконка приложения
        badge: options.badge || '/favicon.ico',
        tag: options.tag || 'task-notification', // Тег для группировки
        data: options.data,
        requireInteraction: options.requireInteraction || false,
        silent: false, // Звук уведомления
      })

      notificationRef.current = notification

      // Обработка клика по уведомлению
      notification.onclick = (event) => {
        event.preventDefault()
        // Фокусируем окно браузера
        window.focus()
        
        // Вызываем кастомный обработчик, если он передан
        if (onClick) {
          onClick()
        }
        
        // Закрываем уведомление
        notification.close()
      }

      // Автоматически закрываем уведомление через 5 секунд
      setTimeout(() => {
        notification.close()
      }, 10000)

      // Обработка закрытия уведомления
      notification.onclose = () => {
        notificationRef.current = null
      }

      return notification
    },
    [isSupported]
  )

  /**
   * Проверяет, есть ли разрешение на уведомления
   */
  const hasPermission = useCallback(() => {
    return isSupported && Notification.permission === 'granted'
  }, [isSupported])

  /**
   * Запрашивает разрешение на уведомления
   */
  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (!isSupported) {
      return false
    }

    if (Notification.permission === 'granted') {
      return true
    }

    const permission = await Notification.requestPermission()
    permissionRef.current = permission
    return permission === 'granted'
  }, [isSupported])

  return {
    isSupported,
    hasPermission: hasPermission(),
    showNotification,
    requestPermission,
  }
}
