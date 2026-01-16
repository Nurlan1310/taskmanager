import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor для добавления CSRF токена
api.interceptors.request.use((config) => {
  const csrfToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1]
  
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken
  }
  
  return config
})

// Response interceptor для обработки ошибок
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Перенаправление на страницу входа только если мы не на странице логина
      // Проверяем URL, чтобы избежать бесконечного редиректа
      const currentPath = window.location.pathname
      if (!currentPath.includes('/login') && !currentPath.includes('/auth')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api

