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
import { Employee } from '@/types/task'
import EmployeeModal from '@/components/EmployeeModal'

interface TaskFormData {
  title: string
  description: string
  due_date: string
  due_time: string
  priority: 'normal' | 'urgent'
  recipients_ids: number[]
  file: File | null
  google_drive_link: string
}

export default function CreateTask() {
  const navigate = useNavigate()
  const { cardId } = useParams<{ cardId?: string }>()
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<TaskFormData>({
    title: '',
    description: '',
    due_date: '',
    due_time: '18:00',
    priority: 'normal',
    recipients_ids: [],
    file: null,
    google_drive_link: '',
  })

  const [selectedRecipients, setSelectedRecipients] = useState<number[]>([])
  const [showRecipientModal, setShowRecipientModal] = useState(false)
  const [uploadedFileName, setUploadedFileName] = useState<string>('')

  const { data: employees } = useQuery<Employee[]>({
    queryKey: ['employees'],
    queryFn: async () => {
      const response = await api.get('/employees/')
      return Array.isArray(response.data) ? response.data : (response.data.results || [])
    },
  })

  const { data: card } = useQuery({
    queryKey: ['card', cardId],
    queryFn: async () => {
      if (!cardId) return null
      const response = await api.get(`/cards/${cardId}/`)
      return response.data
    },
    enabled: !!cardId,
  })

  const createTaskMutation = useMutation({
    mutationFn: async (data: TaskFormData) => {
      // Проверяем, что карточка утверждена, если она с планом
      if (card && card.has_plan && !card.visible) {
        throw new Error('Создание задач недоступно до утверждения плана мероприятия')
      }
      // Проверяем, что карточка активна
      if (card && !card.is_active) {
        throw new Error('Создание задач недоступно: мероприятие еще не началось или уже завершено')
      }
      
      const time = data.due_time || '18:00'
      const dueDate = `${data.due_date}T${time}:00`
      
      // Если есть файл, используем FormData
      if (data.file) {
        const formData = new FormData()
        formData.append('title', data.title)
        formData.append('description', data.description)
        formData.append('priority', data.priority)
        formData.append('due_date', dueDate)
        if (cardId) formData.append('card', cardId)
        selectedRecipients.forEach(id => formData.append('recipients_ids', id.toString()))
        if (data.google_drive_link) formData.append('google_drive_link', data.google_drive_link)
        formData.append('file', data.file)
        
        return api.post('/tasks/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })
      } else {
        // Если файла нет, используем обычный JSON
        const payload: any = {
          title: data.title,
          description: data.description,
          priority: data.priority,
          due_date: dueDate,
          card: cardId ? parseInt(cardId) : null,
          recipients_ids: selectedRecipients,
          google_drive_link: data.google_drive_link,
        }
        
        return api.post('/tasks/', payload)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      if (cardId) {
        queryClient.invalidateQueries({ queryKey: ['card', cardId] })
      }
      navigate(cardId ? `/cards/${cardId}` : '/tasks')
    },
    onError: (error: any) => {
      alert(error?.message || 'Ошибка при создании задачи')
    },
  })

  // Проверяем доступность создания задачи при загрузке
  useEffect(() => {
    if (card) {
      if (card.has_plan && !card.visible) {
        alert('Создание задач недоступно до утверждения плана мероприятия')
        navigate(cardId ? `/cards/${cardId}` : '/tasks')
      } else if (!card.is_active) {
        alert('Создание задач недоступно: мероприятие еще не началось или уже завершено')
        navigate(cardId ? `/cards/${cardId}` : '/tasks')
      }
    }
  }, [card, cardId, navigate])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Проверяем, что карточка утверждена, если она с планом
    if (card && card.has_plan && !card.visible) {
      alert('Создание задач недоступно до утверждения плана мероприятия')
      return
    }
    // Проверяем, что карточка активна
    if (card && !card.is_active) {
      alert('Создание задач недоступно: мероприятие еще не началось или уже завершено')
      return
    }
    
    if (!formData.due_date) {
      alert('Необходимо указать срок выполнения')
      return
    }
    
    if (selectedRecipients.length === 0) {
      alert('Выберите хотя бы одного адресата')
      return
    }
    createTaskMutation.mutate({ ...formData, recipients_ids: selectedRecipients })
  }
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null
    setFormData(prev => ({ ...prev, file }))
    setUploadedFileName(file?.name || '')
  }

  const handleChange = (field: keyof TaskFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const toggleRecipient = (employeeId: number) => {
    setSelectedRecipients(prev =>
      prev.includes(employeeId)
        ? prev.filter(id => id !== employeeId)
        : [...prev, employeeId]
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to={cardId ? `/cards/${cardId}` : '/tasks'}>
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Создать задачу</h1>
          {card && (
            <p className="text-muted-foreground mt-1">
              Мероприятие: {card.title}
            </p>
          )}
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

            <div>
              <label className="text-sm font-medium mb-2 block">
                Адресаты <span className="text-red-500">*</span>
              </label>
              <div className="flex flex-wrap gap-2 mb-2 min-h-[40px] p-2 border rounded-md">
                {selectedRecipients.map((id) => {
                  const emp = employees?.find(e => e.id === id)
                  return emp ? (
                    <div
                      key={id}
                      className="px-3 py-1 bg-primary text-primary-foreground rounded-full text-sm flex items-center gap-2"
                    >
                      {emp.full_name_complete || emp.full_name}
                      <button
                        type="button"
                        onClick={() => toggleRecipient(id)}
                        className="ml-1 hover:bg-primary-foreground/20 rounded-full w-4 h-4 flex items-center justify-center"
                      >
                        ×
                      </button>
                    </div>
                  ) : null
                })}
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowRecipientModal(true)}
              >
                Добавить адресата
              </Button>
              {selectedRecipients.length === 0 && (
                <p className="text-sm text-red-500 mt-1">Выберите хотя бы одного адресата</p>
              )}
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Загрузка файла</label>
              <Input
                type="file"
                onChange={handleFileChange}
                className="cursor-pointer"
              />
              {uploadedFileName && (
                <p className="text-sm text-muted-foreground mt-2">
                  Выбран файл: {uploadedFileName}
                </p>
              )}
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Ссылка на Google Диск</label>
              <Input
                type="url"
                value={formData.google_drive_link}
                onChange={(e) => handleChange('google_drive_link', e.target.value)}
                placeholder="https://drive.google.com/..."
              />
            </div>

            <div className="flex gap-4">
              <Button type="submit" disabled={createTaskMutation.isPending}>
                <Save className="w-4 h-4 mr-2" />
                {createTaskMutation.isPending ? 'Создание...' : 'Создать задачу'}
              </Button>
              <Button type="button" variant="outline" asChild>
                <Link to={cardId ? `/cards/${cardId}` : '/tasks'}>Отмена</Link>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Модальное окно выбора адресатов */}
      <EmployeeModal
        isOpen={showRecipientModal}
        onClose={() => setShowRecipientModal(false)}
        employees={employees || []}
        selectedIds={selectedRecipients}
        onToggle={toggleRecipient}
        title="Выберите адресатов"
      />
    </div>
  )
}

