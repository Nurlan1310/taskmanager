import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { ArrowLeft, Save } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Task } from '@/types/task'

interface TaskFormData {
  title: string
  description: string
  due_date: string
  due_time: string
  priority: 'normal' | 'urgent'
}

export default function EditTask() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  
  const [formData, setFormData] = useState<TaskFormData>({
    title: '',
    description: '',
    due_date: '',
    due_time: '18:00',
    priority: 'normal',
  })

  // Загружаем задачу
  const { data: task, isLoading: isLoadingTask } = useQuery<Task>({
    queryKey: ['task', id],
    queryFn: async () => {
      const response = await api.get(`/tasks/${id}/`)
      return response.data
    },
    enabled: !!id,
  })

  // Заполняем форму данными задачи
  useEffect(() => {
    if (task) {
      // Парсим due_date (может быть в формате ISO или только дата)
      let dueDate = ''
      let dueTime = '18:00'
      
      if (task.due_date) {
        const dateStr = task.due_date
        if (dateStr.includes('T')) {
          // ISO формат с временем
          const date = new Date(dateStr)
          dueDate = date.toISOString().split('T')[0]
          const hours = String(date.getHours()).padStart(2, '0')
          const minutes = String(date.getMinutes()).padStart(2, '0')
          dueTime = `${hours}:${minutes}`
        } else {
          // Только дата
          dueDate = dateStr
        }
      }
      
      setFormData({
        title: task.title || '',
        description: task.description || '',
        due_date: dueDate,
        due_time: dueTime,
        priority: (task.priority as 'normal' | 'urgent') || 'normal',
      })
    }
  }, [task])

  const updateTaskMutation = useMutation({
    mutationFn: async (data: TaskFormData) => {
      const time = data.due_time || '18:00'
      const dueDate = `${data.due_date}T${time}:00`
      
      const payload: any = {
        title: data.title,
        description: data.description,
        priority: data.priority,
        due_date: dueDate,
      }
      
      return api.patch(`/tasks/${id}/`, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      navigate(`/tasks/${id}`)
    },
    onError: (error: any) => {
      alert(error?.response?.data?.error || error?.message || 'Ошибка при обновлении задачи')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.title.trim()) {
      alert('Необходимо указать название задачи')
      return
    }
    
    if (!formData.due_date) {
      alert('Необходимо указать срок выполнения')
      return
    }
    
    updateTaskMutation.mutate(formData)
  }

  const handleChange = (field: keyof TaskFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  if (isLoadingTask) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!task) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground mb-4">Задача не найдена</p>
        <Button asChild>
          <Link to="/tasks">Вернуться к списку</Link>
        </Button>
      </div>
    )
  }

  // Проверяем, можно ли редактировать задачу
  // Редактирование доступно только для статуса revision
  const canEdit = task.status === 'revision'

  if (!canEdit) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground mb-4">
          Редактирование задачи доступно только в статусе "На пересмотрении"
        </p>
        <Button asChild>
          <Link to={`/tasks/${id}`}>Вернуться к задаче</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to={`/tasks/${id}`}>
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Редактировать задачу</h1>
          <p className="text-muted-foreground mt-1">
            Статус: {task.status_display || task.status}
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Информация о задаче</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">
                Название задачи <span className="text-red-500">*</span>
              </label>
              <Input
                value={formData.title}
                onChange={(e) => handleChange('title', e.target.value)}
                placeholder="Введите название задачи"
                required
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Описание</label>
              <Textarea
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder="Описание задачи"
                rows={4}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Срок выполнения <span className="text-red-500">*</span>
                </label>
                <Input
                  type="date"
                  value={formData.due_date}
                  onChange={(e) => handleChange('due_date', e.target.value)}
                  required
                />
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">Время выполнения</label>
                <Input
                  type="time"
                  value={formData.due_time}
                  onChange={(e) => handleChange('due_time', e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Приоритет</label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant={formData.priority === 'normal' ? 'default' : 'outline'}
                  onClick={() => handleChange('priority', 'normal')}
                >
                  Обычная
                </Button>
                <Button
                  type="button"
                  variant={formData.priority === 'urgent' ? 'default' : 'outline'}
                  onClick={() => handleChange('priority', 'urgent')}
                >
                  Срочная
                </Button>
              </div>
            </div>

            <div className="flex gap-4">
              <Button type="submit" disabled={updateTaskMutation.isPending}>
                <Save className="w-4 h-4 mr-2" />
                {updateTaskMutation.isPending ? 'Сохранение...' : 'Сохранить изменения'}
              </Button>
              <Button type="button" variant="outline" asChild>
                <Link to={`/tasks/${id}`}>Отмена</Link>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
