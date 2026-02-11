import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ArrowLeft, Save } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Employee } from '@/types/task'
import EmployeeModal from '@/components/EmployeeModal'
import { useAuthStore } from '@/store/authStore'
import { formatDateInAstanaTime } from '@/lib/dateUtils'
import { toast } from 'sonner'

interface EventCard {
  id: number
  title: string
  start_date: string
  end_date?: string
  is_active: boolean
  visible: boolean
  has_plan: boolean
  plan_status?: 'approved' | 'pending' | 'rejected'
}

interface TaskFormData {
  title: string
  description: string
  due_date: string
  due_time: string
  priority: 'normal' | 'urgent'
  recipients_ids: number[]
  file: File | null
  google_drive_link: string
  is_according_to_plan: boolean
  creation_deputy_id: number | null
  review_self: boolean
  final_reviewer_enabled: boolean
  final_reviewer_id: number | null
}

export default function CreateTask() {
  const navigate = useNavigate()
  const { cardId } = useParams<{ cardId?: string }>()
  const queryClient = useQueryClient()
  const { user } = useAuthStore()
  const [formData, setFormData] = useState<TaskFormData>({
    title: '',
    description: '',
    due_date: '',
    due_time: '18:00',
    priority: 'normal',
    recipients_ids: [],
    file: null,
    google_drive_link: '',
    is_according_to_plan: true,
    creation_deputy_id: null,
    review_self: true,
    final_reviewer_enabled: false,
    final_reviewer_id: null,
  })

  const [selectedRecipients, setSelectedRecipients] = useState<number[]>([])
  const [showRecipientModal, setShowRecipientModal] = useState(false)
  const [uploadedFileName, setUploadedFileName] = useState<string>('')
  const [showCardModal, setShowCardModal] = useState(false)
  const [cardSearchQuery, setCardSearchQuery] = useState('')
  const [selectedCardId, setSelectedCardId] = useState<number | null>(cardId ? parseInt(cardId) : null)
  
  // Определяем роль пользователя
  const userRole = user?.employee?.role || ''
  const needsDeputySelection = !formData.is_according_to_plan && (userRole === 'staff' || userRole === 'senior' || userRole === 'head')
  const isStaff = userRole === 'staff'

  const { data: employees } = useQuery<Employee[]>({
    queryKey: ['employees'],
    queryFn: async () => {
      const response = await api.get('/employees/')
      return Array.isArray(response.data) ? response.data : (response.data.results || [])
    },
  })
  
  // Находим руководителя отдела для обычного сотрудника
  const departmentHead = isStaff && user?.employee?.department?.id
    ? employees?.find(emp => 
        emp.role === 'head' && 
        emp.department?.id === user?.employee?.department?.id
      )
    : null
  
  // Получаем список директора и заместителей для выбора
  const deputiesAndDirector = employees?.filter(emp => 
    emp.role === 'deputy' || emp.role === 'director'
  ) || []

  // Получаем активные мероприятия для модального окна
  const { data: activeCards } = useQuery<EventCard[]>({
    queryKey: ['activeCards', 'forTaskCreation'],
    queryFn: async () => {
      const response = await api.get('/cards/?archive=false')
      const allCards = Array.isArray(response.data) ? response.data : (response.data.results || [])
      // Фильтруем только активные мероприятия, где можно создавать задачи
      return allCards.filter((card: EventCard) => {
        // Активное мероприятие: is_active=true и (visible=true или нет плана или план утвержден)
        return card.is_active && (card.visible || !card.has_plan || card.plan_status === 'approved')
      })
    },
    enabled: showCardModal, // Загружаем только когда модальное окно открыто
  })

  // Фильтруем мероприятия по поисковому запросу
  const filteredCards = activeCards?.filter((card) =>
    card.title.toLowerCase().includes(cardSearchQuery.toLowerCase())
  ) || []

  const { data: card } = useQuery({
    queryKey: ['card', selectedCardId],
    queryFn: async () => {
      if (!selectedCardId) return null
      const response = await api.get(`/cards/${selectedCardId}/`)
      return response.data
    },
    enabled: !!selectedCardId,
  })

  // Синхронизируем selectedCardId с cardId из URL при монтировании
  useEffect(() => {
    if (cardId && !selectedCardId) {
      setSelectedCardId(parseInt(cardId))
    }
  }, [cardId, selectedCardId])

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
        formData.append('is_according_to_plan', data.is_according_to_plan.toString())
        if (selectedCardId) formData.append('card', selectedCardId.toString())
        selectedRecipients.forEach(id => formData.append('recipients_ids', id.toString()))
        if (data.google_drive_link) formData.append('google_drive_link', data.google_drive_link)
        if (data.creation_deputy_id) formData.append('creation_deputy_id', data.creation_deputy_id.toString())
        formData.append('review_self', data.review_self.toString())
        if (data.final_reviewer_enabled && data.final_reviewer_id) formData.append('final_reviewer_id', data.final_reviewer_id.toString())
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
          is_according_to_plan: data.is_according_to_plan,
          card: selectedCardId,
          recipients_ids: selectedRecipients,
          google_drive_link: data.google_drive_link,
        }
        if (data.creation_deputy_id) {
          payload.creation_deputy_id = data.creation_deputy_id
        }
        payload.review_self = data.review_self
        if (data.final_reviewer_enabled && data.final_reviewer_id) {
          payload.final_reviewer_id = data.final_reviewer_id
        }
        
        return api.post('/tasks/', payload)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      if (selectedCardId) {
        queryClient.invalidateQueries({ queryKey: ['card', selectedCardId] })
      }
      toast.success('Задача успешно создана')
      navigate('/assignments')
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
        navigate(selectedCardId ? `/cards/${selectedCardId}` : '/assignments')
      } else if (!card.is_active) {
        alert('Создание задач недоступно: мероприятие еще не началось или уже завершено')
        navigate(selectedCardId ? `/cards/${selectedCardId}` : '/assignments')
      }
    }
  }, [card, selectedCardId, navigate])

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
    
    if (!selectedCardId) {
      alert('Необходимо выбрать мероприятие')
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
    
    // Проверяем выбор заместителя, если требуется
    if (needsDeputySelection && !formData.creation_deputy_id) {
      alert('Необходимо выбрать заместителя для согласования')
      return
    }
    
    if (formData.final_reviewer_enabled && !formData.final_reviewer_id) {
      alert('Необходимо выбрать финального проверяющего')
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
          <Link to={selectedCardId ? `/cards/${selectedCardId}` : '/tasks'}>
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Создать задачу</h1>
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
                Мероприятие <span className="text-red-500">*</span>
              </label>
              {card ? (
                <div className="p-3 border rounded-md bg-muted/50 flex items-center justify-between">
                  <div>
                    <div className="font-medium">{card.title}</div>
                    <div className="text-sm text-muted-foreground mt-1">
                      {formatDateInAstanaTime(card.start_date)}
                      {card.end_date && ` — ${formatDateInAstanaTime(card.end_date)}`}
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelectedCardId(null)
                      setShowCardModal(true)
                    }}
                  >
                    Изменить
                  </Button>
                </div>
              ) : (
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  onClick={() => setShowCardModal(true)}
                >
                  Выбрать мероприятие
                </Button>
              )}
            </div>

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

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Создание задачи
                </label>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant={formData.is_according_to_plan ? 'default' : 'outline'}
                    onClick={() => handleChange('is_according_to_plan', true)}
                  >
                    Согласно плана
                  </Button>
                  <Button
                    type="button"
                    variant={!formData.is_according_to_plan ? 'default' : 'outline'}
                    onClick={() => handleChange('is_according_to_plan', false)}
                  >
                    Не согласно плана
                  </Button>
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
            </div>

            <div className="space-y-4">
              <label className="text-sm font-medium mb-2 block">
                Проверка выполнения
              </label>
              <p className="text-xs text-muted-foreground mb-2">
                Кто будет проверять выполнение задачи (после сдачи исполнителем)
              </p>
              <div className="flex flex-wrap gap-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm">Проверить самому:</span>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant={formData.review_self ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => handleChange('review_self', true)}
                    >
                      Да
                    </Button>
                    <Button
                      type="button"
                      variant={!formData.review_self ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => handleChange('review_self', false)}
                    >
                      Нет
                    </Button>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm">Финальный проверяющий:</span>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant={formData.final_reviewer_enabled ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => handleChange('final_reviewer_enabled', true)}
                    >
                      Да
                    </Button>
                    <Button
                      type="button"
                      variant={!formData.final_reviewer_enabled ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => {
                        handleChange('final_reviewer_enabled', false)
                        handleChange('final_reviewer_id', null)
                      }}
                    >
                      Нет
                    </Button>
                  </div>
                </div>
              </div>
              {formData.final_reviewer_enabled && (
                <div className="mt-2">
                  <label className="text-sm font-medium mb-2 block">
                    Выберите финального проверяющего <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.final_reviewer_id || ''}
                    onChange={(e) => handleChange('final_reviewer_id', e.target.value ? parseInt(e.target.value) : null)}
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    <option value="">Выберите заместителя или директора</option>
                    {deputiesAndDirector.map((person) => (
                      <option key={person.id} value={person.id}>
                        {person.full_name_complete || person.full_name}
                        {person.position && ` (${person.position})`}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {needsDeputySelection && (
              <>
                {/* Показываем заблокированного руководителя отдела для обычного сотрудника */}
                {isStaff && departmentHead && (
                  <div>
                    <label className="text-sm font-medium mb-2 block">
                      Руководитель отдела для согласования
                    </label>
                    <div className="w-full px-3 py-2 border rounded-md bg-muted/50 text-muted-foreground cursor-not-allowed">
                      {departmentHead.full_name_complete || departmentHead.full_name}
                      {departmentHead.position && ` (${departmentHead.position})`}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Задача будет отправлена на согласование вашему руководителю отдела
                    </p>
                  </div>
                )}
                
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Согласующий <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.creation_deputy_id || ''}
                    onChange={(e) => handleChange('creation_deputy_id', e.target.value ? parseInt(e.target.value) : null)}
                    className="w-full px-3 py-2 border rounded-md"
                    required
                  >
                    <option value="">Выберите согласующего</option>
                    {deputiesAndDirector.map((person) => (
                      <option key={person.id} value={person.id}>
                        {person.full_name_complete || person.full_name} 
                        {person.position && ` (${person.position})`}
                      </option>
                    ))}
                  </select>
                </div>
              </>
            )}

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
                <Link to={selectedCardId ? `/cards/${selectedCardId}` : '/tasks'}>Отмена</Link>
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

      {/* Модальное окно выбора мероприятия */}
      <Dialog 
        open={showCardModal} 
        onOpenChange={(open) => {
          setShowCardModal(open)
          if (!open) setCardSearchQuery('')
        }}
        centered
        maxWidth="xl"
      >
        <DialogContent onClose={() => {
          setShowCardModal(false)
          setCardSearchQuery('')
        }}>
          <DialogHeader>
            <DialogTitle>Выберите мероприятие</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <div className="mb-4">
              <Input
                type="text"
                placeholder="Поиск мероприятия..."
                value={cardSearchQuery}
                onChange={(e) => setCardSearchQuery(e.target.value)}
              />
            </div>
            {activeCards && activeCards.length > 0 ? (
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {filteredCards.length > 0 ? (
                  filteredCards.map((card) => (
                    <button
                      key={card.id}
                      type="button"
                      onClick={() => {
                        setSelectedCardId(card.id)
                        setShowCardModal(false)
                        setCardSearchQuery('')
                      }}
                      className="w-full text-left p-4 border rounded-lg hover:bg-accent transition-colors"
                    >
                      <div className="font-semibold">{card.title}</div>
                      <div className="text-sm text-muted-foreground mt-1">
                        {formatDateInAstanaTime(card.start_date)}
                        {card.end_date && ` — ${formatDateInAstanaTime(card.end_date)}`}
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    Не найдено мероприятий по запросу
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                Нет доступных активных мероприятий
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

