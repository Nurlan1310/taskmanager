import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { CheckSquare } from 'lucide-react'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuthStore()
  const navigate = useNavigate()

  // Получаем CSRF cookie перед первой попыткой логина
  useEffect(() => {
    api.get('/auth/csrf/').catch(() => {
      // в dev можно тихо игнорировать ошибку
    })
  }, [])

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (loading) return // Предотвращаем повторную отправку
    
    setError('')
    setLoading(true)

    try {
      await login(username, password)
      navigate('/')
    } catch (err: any) {
      console.error('Login error:', err) // Для отладки
      const errorData = err.response?.data
      if (errorData?.error_type === 'user_not_found') {
        setError('Пользователь с таким логином не существует')
      } else if (errorData?.error_type === 'invalid_password') {
        setError('Неверный пароль')
      } else {
        setError(errorData?.error || 'Неверное имя пользователя или пароль')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/10 via-background to-primary/5">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center">
              <CheckSquare className="w-10 h-10 text-white" />
            </div>
          </div>
          <CardTitle className="text-2xl">Добро пожаловать</CardTitle>
          <CardDescription>Введите свои учетные данные для входа</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                {error}
              </div>
            )}
            <div>
              <label className="text-sm font-medium mb-2 block">Имя пользователя</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                required
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Пароль</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Вход...' : 'Войти'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

