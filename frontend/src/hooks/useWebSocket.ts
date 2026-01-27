import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuthStore } from '@/store/authStore'

interface WebSocketMessage {
  type: string
  data?: any
  message?: string
}

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void
  onError?: (error: Event) => void
  onConnect?: () => void
  onDisconnect?: () => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    onMessage,
    onError,
    onConnect,
    onDisconnect,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
  } = options

  const { isAuthenticated } = useAuthStore()
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  
  // Используем refs для callbacks, чтобы избежать пересоздания connect
  const onMessageRef = useRef(onMessage)
  const onErrorRef = useRef(onError)
  const onConnectRef = useRef(onConnect)
  const onDisconnectRef = useRef(onDisconnect)
  
  // Обновляем refs при изменении callbacks
  useEffect(() => {
    onMessageRef.current = onMessage
    onErrorRef.current = onError
    onConnectRef.current = onConnect
    onDisconnectRef.current = onDisconnect
  }, [onMessage, onError, onConnect, onDisconnect])

  const connect = useCallback(() => {
    if (!isAuthenticated) {
      return
    }

    // Если уже есть активное соединение, не создаем новое
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return
    }

    // Определяем WebSocket URL
    // В режиме разработки подключаемся напрямую к Django (минуя Vite прокси)
    // В продакшене используем относительный путь
    const isDevelopment = import.meta.env.DEV
    let wsUrl: string
    
    if (isDevelopment) {
      // В разработке подключаемся напрямую к Django на порту 8001
      wsUrl = 'ws://localhost:8001/ws/notifications/'
    } else {
      // В продакшене используем относительный путь (через тот же домен)
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      wsUrl = `${protocol}//${host}/ws/notifications/`
    }

    try {
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        reconnectAttemptsRef.current = 0
        onConnectRef.current?.()
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          
          // Обработка ping/pong для поддержания соединения
          if (message.type === 'pong') {
            return
          }

          // Логирование для отладки
          console.log('WebSocket message received:', message)
          
          onMessageRef.current?.(message)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error, event.data)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        onErrorRef.current?.(error)
      }

      ws.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason)
        setIsConnected(false)
        onDisconnectRef.current?.()

        // Автоматическое переподключение только если это не было намеренное закрытие
        // Код 1000 = нормальное закрытие, не переподключаемся
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++
          console.log(`Reconnecting... Attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts}`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectInterval)
        } else if (event.code === 1000) {
          // Нормальное закрытие - сбрасываем счетчик попыток
          reconnectAttemptsRef.current = 0
        } else {
          console.error('Max reconnection attempts reached')
        }
      }

      wsRef.current = ws
    } catch (error) {
      console.error('Error creating WebSocket:', error)
    }
  }, [isAuthenticated, reconnectInterval, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  const send = useCallback((data: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  // Подключение при монтировании и изменении isAuthenticated
  useEffect(() => {
    if (isAuthenticated) {
      connect()
    } else {
      disconnect()
    }

    return () => {
      disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]) // Убираем connect и disconnect из зависимостей, чтобы избежать циклов

  // Отправка ping каждые 30 секунд для поддержания соединения
  useEffect(() => {
    if (!isConnected) return

    const pingInterval = setInterval(() => {
      send({ type: 'ping' })
    }, 30000)

    return () => {
      clearInterval(pingInterval)
    }
  }, [isConnected, send])

  return {
    isConnected,
    send,
    connect,
    disconnect,
  }
}