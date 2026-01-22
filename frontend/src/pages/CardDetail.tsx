import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ArrowLeft, Plus, Calendar, User, CheckCircle2, Upload, X, Clock, FileText, Filter, Circle, AlertCircle, Edit, BarChart3 } from 'lucide-react'
import { formatDateInAstanaTime, formatDateTimeInAstanaTime } from '@/lib/dateUtils'
import { useState } from 'react'
import { TaskStatus, Employee } from '@/types/task'
import { Select } from '@/components/ui/select'
import { useAuthStore } from '@/store/authStore'

interface EventCard {
  id: number
  title: string
  description?: string
  start_date: string
  end_date?: string
  created_by: {
    id: number
    user: {
      first_name: string
      last_name: string
    }
  }
  responsible_department?: {
    id: number
    name: string
  }
  progress: number
  approval_count: number
  urgent_count: number
  other_count: number
  done_count?: number
  total_tasks?: number
  user_progress?: number
  user_done_tasks?: number
  user_total_tasks?: number
  department_progress?: number
  department_done_tasks?: number
  department_total_tasks?: number
  categories: Array<{ id: number; name: string; slug: string }>
  tasks: any[]
  has_plan?: boolean
  plan_status?: 'draft' | 'pending' | 'rejected' | 'approved'
  plan_file?: string
  plan_submitted_at?: string
  plan_approved_at?: string
  plan_rejected_reason?: string
  visible?: boolean
  is_active?: boolean
  current_approver_index?: number
  approvers?: Array<{
    id: number
    user: { first_name: string; last_name: string }
    position: string
  }>
  final_approver?: {
    id: number
    user: { first_name: string; last_name: string }
    position: string
  }
}

const statusLabels: Record<TaskStatus, string> = {
  new: 'Новая',
  in_progress: 'В работе',
  done: 'Выполнена',
  under_review: 'На проверке',
  sent_for_review: 'Отправлено на проверку',
  rejected: 'Отклонена',
  pending: 'На согласовании',
  revision: 'На пересмотрении',
  send_for_approve: 'Отправлено на согласование',
}

const statusColors: Record<TaskStatus, string> = {
  new: 'bg-gray-500',
  in_progress: 'bg-yellow-500',
  done: 'bg-green-500',
  under_review: 'bg-blue-500',
  sent_for_review: 'bg-purple-500',
  rejected: 'bg-red-500',
  pending: 'bg-orange-500',
  revision: 'bg-amber-500',
  send_for_approve: 'bg-indigo-500',
}

type TaskScope = 'mine' | 'department' | 'all'
type TaskTypeFilter = 'all' | 'normal' | 'approval'

export default function CardDetail() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [correctedPlanFile, setCorrectedPlanFile] = useState<File | null>(null)
  const [showApprovalTimeline, setShowApprovalTimeline] = useState(false)
  const [showEditDialog, setShowEditDialog] = useState(false)
  const [scopeFilter, setScopeFilter] = useState<TaskScope>('mine')
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all')
  const [typeFilter, setTypeFilter] = useState<TaskTypeFilter>('all')
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(null)
  
  // Состояние для редактирования карточки
  const [editDescription, setEditDescription] = useState('')
  const [editStartDate, setEditStartDate] = useState('')
  const [editEndDate, setEditEndDate] = useState('')

  const { data: card, isLoading } = useQuery<EventCard>({
    queryKey: ['card', id],
    queryFn: async () => {
      const response = await api.get(`/cards/${id}/`)
      return response.data
    },
  })

  const { data: currentUser } = useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const response = await api.get('/auth/me/')
      return response.data
    },
  })

  // Проверяем права доступа
  const canViewAll = currentUser?.employee?.role === 'director' || currentUser?.employee?.role === 'deputy'
  const isHead = currentUser?.employee?.role === 'head'
  const userDepartmentId = currentUser?.employee?.department?.id

  // Получаем список сотрудников для фильтрации
  const { data: employees } = useQuery<Employee[]>({
    queryKey: ['employees'],
    queryFn: async () => {
      const response = await api.get('/employees/')
      return Array.isArray(response.data) ? response.data : (response.data.results || [])
    },
  })

  // Фильтруем сотрудников в зависимости от роли и выбранного scope
  const availableEmployees = employees?.filter((emp) => {
    if (scopeFilter === 'department') {
      // При выборе "Задачи моего отдела" показываем только сотрудников этого отдела
      if (userDepartmentId) {
        return emp.department?.id === userDepartmentId
      }
      return false
    }
    if (canViewAll && scopeFilter === 'all') {
      // Директор и заместитель при выборе "Все задачи" видят всех
      return true
    }
    if (isHead && userDepartmentId) {
      return emp.department?.id === userDepartmentId // Руководитель видит свой отдел
    }
    return emp.id === currentUser?.employee?.id // Обычный сотрудник видит только себя
  }) || []

  const isCreator = currentUser?.employee?.id === card?.created_by?.id
  const canUploadCorrectedPlan = isCreator && card?.plan_status === 'rejected'
  
  // Инициализация данных для редактирования
  const initializeEditData = () => {
    if (card) {
      setEditDescription(card.description || '')
      const startDate = new Date(card.start_date)
      setEditStartDate(formatDateLocal(startDate))
      if (card.end_date) {
        const endDate = new Date(card.end_date)
        setEditEndDate(formatDateLocal(endDate))
      } else {
        setEditEndDate('')
      }
    }
  }
  
  // Функция для форматирования даты в YYYY-MM-DD (локальное время)
  const formatDateLocal = (date: Date): string => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  
  // Мутация для обновления карточки
  const updateCardMutation = useMutation({
    mutationFn: async (data: { description?: string; start_date?: string; end_date?: string | null }) => {
      return api.patch(`/cards/${id}/`, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['card', id] })
      setShowEditDialog(false)
    },
    onError: (error: any) => {
      console.error('Ошибка при обновлении карточки:', error)
      alert(error?.response?.data?.error || 'Ошибка при обновлении карточки')
    },
  })
  
  const handleEditCard = () => {
    if (!card) return
    initializeEditData()
    setShowEditDialog(true)
  }
  
  const handleSaveEdit = () => {
    if (!editStartDate) {
      alert('Необходимо указать дату начала')
      return
    }
    
    updateCardMutation.mutate({
      description: editDescription,
      start_date: editStartDate,
      end_date: editEndDate || null,
    })
  }
  
  const handleStatistics = () => {
    if (!card || !user?.employee?.department?.id) return
    
    // Переходим на страницу статистики с предустановленными фильтрами
    const params = new URLSearchParams()
    params.set('card_id', card.id.toString())
    params.set('department_id', user.employee.department.id.toString())
    // employee_id не устанавливаем (пустой) - это означает "все сотрудники отдела"
    params.set('filter_mode', 'event')
    
    navigate(`/statistics?${params.toString()}`)
  }

  const uploadCorrectedPlanMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('corrected_plan_file', file)
      return api.post(`/cards/${id}/upload-corrected-plan/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['card', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setCorrectedPlanFile(null)
      alert('Исправленный план успешно загружен и отправлен на повторное согласование.')
    },
    onError: (error: any) => {
      console.error('Ошибка при загрузке исправленного плана:', error)
      alert(error?.response?.data?.error || 'Ошибка при загрузке исправленного плана')
    },
  })

  const handleUploadCorrectedPlan = () => {
    if (correctedPlanFile) {
      uploadCorrectedPlanMutation.mutate(correctedPlanFile)
    } else {
      alert('Пожалуйста, выберите файл для загрузки.')
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!card) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground mb-4">Мероприятие не найдено</p>
        <Button asChild>
          <Link to="/cards">Вернуться к списку</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <Button variant="ghost" size="icon" asChild className="mt-1">
          <Link to="/cards">
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">{card.title}</h1>
          <div className="flex flex-wrap gap-2 mt-2">
            {card.categories && card.categories.length > 0 && card.categories.map((cat) => (
              <Badge key={cat.id} variant="secondary">
                {cat.name}
              </Badge>
            ))}
            {card.has_plan && card.plan_status !== 'approved' && (
              <Badge 
                variant={
                  card.plan_status === 'pending' ? 'default' :
                  card.plan_status === 'rejected' ? 'destructive' :
                  'secondary'
                }
                className={
                  card.plan_status === 'pending' ? 'bg-yellow-500' :
                  card.plan_status === 'rejected' ? 'bg-red-500' :
                  ''
                }
              >
                {card.plan_status === 'pending' ? 'На согласовании' :
                 card.plan_status === 'rejected' ? 'План отклонён' :
                 'Черновик'}
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Информация о мероприятии */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Информация</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {card.description && (
              <div>
                <h3 className="font-semibold mb-1 text-sm">Описание</h3>
                <p className="text-sm text-muted-foreground">{card.description}</p>
              </div>
            )}

            <div className="flex items-center gap-2 text-sm">
              <Calendar className="w-4 h-4 text-muted-foreground" />
              <span className="text-muted-foreground">Период:</span>
              <span>
                {formatDateInAstanaTime(card.start_date)}
                {card.end_date && ` — ${formatDateInAstanaTime(card.end_date)}`}
              </span>
            </div>

            {card.responsible_department && (
              <div className="flex items-start gap-2 text-sm">
                <User className="w-4 h-4 text-muted-foreground" />
                <span className="text-muted-foreground">Отдел:</span>
                <span>{card.responsible_department.name}</span>
              </div>
            )}

         

            {card.has_plan && (
              <div className="pt-3 border-t space-y-3">
                <h3 className="font-semibold text-sm">Информация о плане</h3>
                {card.plan_file && (
                  <div className="text-sm">
                    <a
                      href={card.plan_file}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline flex items-center gap-2"
                    >
                      <FileText className="w-4 h-4" />
                      Скачать план мероприятия
                    </a>
                  </div>
                )}
                <div className="flex items-center gap-3">
                  {card.plan_status === 'approved' && (
                    <Badge variant="default" className="bg-green-500">
                      План утверждён
                    </Badge>
                  )}
                  {card.plan_status === 'rejected' && (
                    <Badge variant="destructive" className="bg-red-500">
                      План отклонён
                    </Badge>
                  )}
                  {card.plan_status === 'pending' && (
                    <Badge variant="default" className="bg-yellow-500">
                      На согласовании
                    </Badge>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowApprovalTimeline(true)}
                  >
                    Процесс согласования
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>


        {/* Прогресс */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Прогресс</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Общий прогресс */}
              <div>
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="text-muted-foreground">Общий</span>
                  <span className="font-semibold">
                    {card.done_count || 0}/{card.total_tasks || 0} ({Math.round(card.progress || 0)}%)
                  </span>
                </div>
                <div className="w-full bg-secondary rounded-full h-3">
                  <div
                    className="bg-primary rounded-full h-3 transition-all"
                    style={{ width: `${Math.round(card.progress || 0)}%` }}
                  />
                </div>
              </div>

              {/* Прогресс пользователя */}
              {card.user_total_tasks !== undefined && card.user_total_tasks > 0 && (
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-muted-foreground">Мой</span>
                    <span className="font-medium text-xs">
                      {card.user_done_tasks || 0}/{card.user_total_tasks || 0} ({Math.round(card.user_progress || 0)}%)
                    </span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div
                      className="bg-primary rounded-full h-2 transition-all"
                      style={{ width: `${Math.round(card.user_progress || 0)}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Прогресс отдела */}
              {card.department_total_tasks !== undefined && card.department_total_tasks > 0 && (
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-muted-foreground">Отдел</span>
                    <span className="font-medium text-xs">
                      {card.department_done_tasks || 0}/{card.department_total_tasks || 0} ({Math.round(card.department_progress || 0)}%)
                    </span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div
                      className="bg-primary rounded-full h-2 transition-all"
                      style={{ width: `${Math.round(card.department_progress || 0)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Действия */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Действия</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {/* Кнопка "Создать задачу" */}
              <Button 
                asChild={(card.has_plan ? card.visible : true) && card.is_active}
                disabled={(card.has_plan && !card.visible) || !card.is_active}
                className="w-full"
                variant="default"
              >
                {(card.has_plan && !card.visible) || !card.is_active ? (
                  <span className="flex items-center">
                    <Plus className="w-4 h-4 mr-2" />
                    Создать задачу
                  </span>
                ) : (
                  <Link to={`/cards/${id}/tasks/new`} className="flex items-center">
                    <Plus className="w-4 h-4 mr-2" />
                    Создать задачу
                  </Link>
                )}
              </Button>
              
              {/* Кнопка "Редактировать" (только для создателя) */}
              {isCreator && (
                <Button 
                  variant="outline"
                  className="w-full"
                  onClick={handleEditCard}
                >
                  <Edit className="w-4 h-4 mr-2" />
                  Редактировать
                </Button>
              )}
              
              {/* Кнопка "Статистика" */}
              <Button 
                variant="outline"
                className="w-full"
                onClick={handleStatistics}
                disabled={!user?.employee?.department?.id}
              >
                <BarChart3 className="w-4 h-4 mr-2" />
                Статистика
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Задачи мероприятия */}
      <Card>
        <CardHeader>
          <CardTitle>Задачи мероприятия</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Фильтры */}
          <Card className="mb-6">
            <CardContent className="p-4">
              <div className="flex flex-wrap items-center gap-3">
                {/* Фильтр по области видимости */}
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">Фильтр:</span>
                  <div className="flex gap-1">
                    <Button
                      variant={scopeFilter === 'mine' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => {
                        setScopeFilter('mine')
                        setSelectedEmployeeId(null)
                      }}
                      className="h-8 px-2 text-xs"
                    >
                      <User className="w-3 h-3 mr-1" />
                      Мои
                    </Button>
                    <Button
                      variant={scopeFilter === 'department' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => {
                        setScopeFilter('department')
                        setSelectedEmployeeId(null)
                      }}
                      className="h-8 px-2 text-xs"
                    >
                      <Filter className="w-3 h-3 mr-1" />
                      Отдел
                    </Button>
                    {canViewAll && (
                      <Button
                        variant={scopeFilter === 'all' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => {
                          setScopeFilter('all')
                          setSelectedEmployeeId(null)
                        }}
                        className="h-8 px-2 text-xs"
                      >
                        Все
                      </Button>
                    )}
                  </div>
                </div>

                {/* Выбор сотрудника (для руководителя и директора) */}
                {(isHead || canViewAll) && scopeFilter !== 'mine' && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">Сотрудник:</span>
                    <Select
                      value={selectedEmployeeId?.toString() || ''}
                      onChange={(e) => setSelectedEmployeeId(e.target.value ? parseInt(e.target.value) : null)}
                      className="h-8 text-xs min-w-[150px]"
                    >
                      <option value="">Все</option>
                      {availableEmployees.map((emp) => (
                        <option key={emp.id} value={emp.id}>
                          {emp.full_name}
                          {emp.position && ` (${emp.position})`}
                        </option>
                      ))}
                    </Select>
                  </div>
                )}

                {/* Фильтр по типу */}
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">Тип:</span>
                  <div className="flex gap-1">
                    <Button
                      variant={typeFilter === 'all' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setTypeFilter('all')}
                      className="h-8 px-2 text-xs"
                    >
                      Все
                    </Button>
                    <Button
                      variant={typeFilter === 'normal' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setTypeFilter('normal')}
                      className="h-8 px-2 text-xs"
                    >
                      Обычные
                    </Button>
                    <Button
                      variant={typeFilter === 'approval' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setTypeFilter('approval')}
                      className="h-8 px-2 text-xs"
                    >
                      Согласования
                    </Button>
                  </div>
                </div>

                {/* Фильтры по статусу */}
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">Статус:</span>
                  <div className="flex flex-wrap gap-1">
                    <Button
                      variant={statusFilter === 'all' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setStatusFilter('all')}
                      className="h-8 px-2 text-xs"
                    >
                      <Filter className="w-3 h-3 mr-1" />
                      Активные
                    </Button>
                    <Button
                      variant={statusFilter === 'new' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setStatusFilter('new')}
                      className="h-8 px-2 text-xs"
                    >
                      <Circle className="w-3 h-3 mr-1" />
                      Новые
                    </Button>
                    <Button
                      variant={statusFilter === 'in_progress' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setStatusFilter('in_progress')}
                      className="h-8 px-2 text-xs"
                    >
                      <Clock className="w-3 h-3 mr-1" />
                      В работе
                    </Button>
                    <Button
                      variant={statusFilter === 'under_review' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setStatusFilter('under_review')}
                      className="h-8 px-2 text-xs"
                    >
                      <FileText className="w-3 h-3 mr-1" />
                      На проверке
                    </Button>
                    <Button
                      variant={statusFilter === 'done' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setStatusFilter('done')}
                      className="h-8 px-2 text-xs"
                    >
                      <CheckCircle2 className="w-3 h-3 mr-1" />
                      Выполненные
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {card.tasks && card.tasks.length > 0 ? (
            <div className="space-y-3">
              {card.tasks
                .filter((task: any) => {
                  // Фильтр по области видимости
                  if (selectedEmployeeId) {
                    // Если выбран конкретный сотрудник, показываем только его задачи
                    if (task.assigned_employee?.id !== selectedEmployeeId && 
                        !task.recipients?.some((r: Employee) => r.id === selectedEmployeeId)) {
                      return false
                    }
                  } else {
                    // Фильтр по scope
                    if (scopeFilter === 'mine') {
                      // Мои задачи - только те, которые назначены мне
                      if (task.assigned_employee?.id !== currentUser?.employee?.id &&
                          !task.recipients?.some((r: Employee) => r.id === currentUser?.employee?.id)) {
                        return false
                      }
                    } else if (scopeFilter === 'department') {
                      // Задачи моего отдела - задачи назначенные отделу или сотрудникам отдела
                      if (userDepartmentId) {
                        const isDepartmentTask = task.assigned_department?.id === userDepartmentId ||
                          task.assigned_employee?.department?.id === userDepartmentId
                        if (!isDepartmentTask) {
                          return false
                        }
                      } else {
                        return false
                      }
                    } else if (scopeFilter === 'all') {
                      // Все задачи - показываем все (только для директора/заместителя)
                      if (!canViewAll) {
                        return false
                      }
                    }
                  }

                  // Фильтр по статусу
                  if (statusFilter !== 'all' && task.status !== statusFilter) {
                    return false
                  }
                  // Фильтр по типу
                  if (typeFilter === 'approval') {
                    // Показываем только задачи на согласование (approval и review)
                    return task.task_type === 'approval' || task.task_type === 'review'
                  } else if (typeFilter === 'normal') {
                    // Показываем обычные задачи (исключаем approval и review)
                    return task.task_type !== 'approval' && task.task_type !== 'review'
                  }
                  // typeFilter === 'all' - показываем все задачи
                  return true
                })
                .map((task: any) => {
                  const isUrgent = task.due_date && new Date(task.due_date) <= new Date(Date.now() + 3 * 24 * 60 * 60 * 1000)
                  return (
                    <Link
                      key={task.id}
                      to={`/tasks/${task.id}`}
                      className="block p-4 border rounded-lg hover:bg-accent transition-colors"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <h3 className="font-semibold text-lg">{task.title}</h3>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              {task.priority === 'urgent' && (
                                <Badge variant="destructive">
                                  <AlertCircle className="w-3 h-3 mr-1" />
                                  Срочно
                                </Badge>
                              )}
                              {(task.task_type === 'approval' || task.task_type === 'review') && (
                                <Badge variant="default" className="bg-blue-500">
                                  {task.task_type === 'approval' ? 'Согласование' : 'Проверка'}
                                </Badge>
                              )}
                              <Badge className={statusColors[task.status as TaskStatus]}>
                                {statusLabels[task.status as TaskStatus]}
                              </Badge>
                            </div>
                          </div>

                          <div className="space-y-2 text-sm text-muted-foreground">
                            {/* Первая строка: срок и От кого */}
                            <div className="flex flex-wrap gap-4">
                              {task.due_date && (
                                <div className="flex items-center gap-1">
                                  <Calendar className="w-4 h-4" />
                                  <span className={isUrgent && task.status !== 'done' ? 'text-red-500 font-medium' : ''}>
                                    {formatDateTimeInAstanaTime(task.due_date)}
                                  </span>
                                </div>
                              )}
                              {task.created_by && (
                                <div className="flex items-center gap-1 flex-wrap">
                                  <User className="w-4 h-4" />
                                  <span>
                                    От: {task.created_by.full_name}
                                  </span>
                                  {(task.status === 'sent_for_review' || task.status === 'under_review') && task.current_reviewer && (
                                    <>
                                      <span className="mx-1">•</span>
                                      <User className="w-4 h-4" />
                                      <span>
                                        Проверяет: {task.current_reviewer.full_name}
                                      </span>
                                    </>
                                  )}
                                </div>
                              )}
                            </div>
                            {/* Вторая строка: название мероприятия и Исполнитель */}
                            <div className="flex flex-wrap gap-4">
                              {task.card_title && (
                                <div className="flex items-center gap-1">
                                  <FileText className="w-4 h-4" />
                                  <Link
                                    to={`/cards/${task.card || id}`}
                                    className="text-primary hover:underline"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    {task.card_title}
                                  </Link>
                                </div>
                              )}
                              {task.assigned_employee && (
                                <div className="flex items-center gap-1">
                                  <User className="w-4 h-4" />
                                  <span>
                                    Исполнитель: {task.assigned_employee.full_name}
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    </Link>
                  )
                })}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-muted-foreground mb-4">Нет задач в этом мероприятии</p>
              <div className="relative inline-block group">
                <Button 
                  asChild={card.has_plan ? card.visible : true}
                  disabled={card.has_plan && !card.visible}
                  className="h-10"
                >
                  {card.has_plan && !card.visible ? (
                    <span className="flex items-center">
                      <Plus className="w-4 h-4 mr-2" />
                      Создать задачу
                    </span>
                  ) : (
                    <Link to={`/cards/${id}/tasks/new`}>
                      <Plus className="w-4 h-4 mr-2" />
                      Создать задачу
                    </Link>
                  )}
                </Button>
                {card.has_plan && !card.visible && (
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                    Создание задач недоступно до утверждения плана
                    <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Модальное окно с таймлайном согласования */}
      {card.has_plan && (
        <Dialog open={showApprovalTimeline} onOpenChange={setShowApprovalTimeline}>
          <DialogContent onClose={() => setShowApprovalTimeline(false)}>
            <DialogHeader>
              <DialogTitle>Процесс согласования плана</DialogTitle>
            </DialogHeader>
            <div className="py-8">
              {/* Определяем, кто отклонил план и кто согласовал */}
              {(() => {
                // Находим задачу, которая была отклонена
                const rejectedTask = card.tasks?.find((t: any) => 
                  t.task_type === 'approval' && t.status === 'rejected'
                )
                const rejectionHistory = rejectedTask?.history?.find((h: any) => h.action === 'rejected')
                const rejectedAt = rejectionHistory?.timestamp
                
                // Определяем, на каком шаге произошло отклонение
                let rejectedAtStep: number | 'final' | -1 = -1
                if (rejectedTask) {
                  const approverIndex = card.approvers?.findIndex((a: any) => a.id === rejectedTask.assigned_employee?.id)
                  if (approverIndex !== undefined && approverIndex !== -1) {
                    rejectedAtStep = approverIndex
                  } else if (rejectedTask.assigned_employee?.id === card.final_approver?.id) {
                    rejectedAtStep = 'final'
                  }
                }

                // Находим всех, кто согласовал до отклонения (из истории задач) и их даты согласования
                const approvedBeforeRejection = new Set<number>()
                const approverApprovalDates = new Map<number, string>()
                if (card.tasks) {
                  card.tasks
                    .filter((t: any) => t.task_type === 'approval' && t.status === 'done')
                    .forEach((task: any) => {
                      const approvedHistory = task.history?.find((h: any) => h.action === 'approved' || h.action === 'done')
                      if (approvedHistory && task.assigned_employee) {
                        const approverId = task.assigned_employee.id
                        const approverIndex = card.approvers?.findIndex((a: any) => a.id === approverId)
                        if (approverIndex !== undefined && approverIndex !== -1) {
                          // Сохраняем дату согласования
                          if (approvedHistory.timestamp) {
                            approverApprovalDates.set(approverIndex, approvedHistory.timestamp)
                          }
                          // Проверяем, что это было до отклонения
                          if (card.plan_status === 'rejected' && rejectedAt && approvedHistory.timestamp && approvedHistory.timestamp < rejectedAt) {
                            approvedBeforeRejection.add(approverIndex)
                          } else if (card.plan_status !== 'rejected') {
                            approvedBeforeRejection.add(approverIndex)
                          }
                        }
                      }
                    })
                }

                // Собираем все шаги таймлайна
                const steps: Array<{
                  type: 'upload' | 'approver' | 'final'
                  index?: number
                  approver?: any
                  isCurrent: boolean
                  isCompleted: boolean
                  isRejected: boolean
                  isRejectedAt: boolean
                  approvalDate?: string
                }> = []

                // Шаг 1: Загрузка плана
                const uploadIsCurrent = card.plan_status === 'rejected'
                const uploadIsCompleted = !!(card.plan_submitted_at && card.plan_status !== 'rejected')
                steps.push({
                  type: 'upload',
                  isCurrent: uploadIsCurrent,
                  isCompleted: uploadIsCompleted,
                  isRejected: false,
                  isRejectedAt: false
                })

                // Шаги: Согласующие
                card.approvers?.forEach((approver: any, index: number) => {
                  const wasApprovedBeforeRejection = approvedBeforeRejection.has(index)
                  const approvalDate = approverApprovalDates.get(index)
                  const isRejectedAt = rejectedAtStep === index
                  const isRejected = card.plan_status === 'rejected' && !wasApprovedBeforeRejection && !isRejectedAt
                  const isCompleted = card.plan_status === 'rejected' 
                    ? wasApprovedBeforeRejection
                    : index < (card.current_approver_index || 0)
                  const isCurrent = !!(card.plan_status === 'pending' && 
                    index === (card.current_approver_index || 0) && !isRejected)
                  
                  steps.push({
                    type: 'approver',
                    index,
                    approver,
                    isCurrent: isCurrent && !isRejected,
                    isCompleted: isCompleted && !isRejected,
                    isRejected: isRejected && !isRejectedAt,
                    isRejectedAt: !!isRejectedAt,
                    approvalDate: approvalDate
                  })
                })

                // Шаг: Финальный утверждающий
                if (card.final_approver) {
                  const finalIsRejectedAt = rejectedAtStep === 'final'
                  const finalIsRejected = !!(card.plan_status === 'rejected' && rejectedAtStep === 'final')
                  const finalIsCompleted = card.plan_status === 'approved'
                  const finalIsCurrent = !!((card.current_approver_index || 0) >= (card.approvers?.length || 0) && 
                                         card.plan_status === 'pending' && !finalIsRejected)
                  
                  steps.push({
                    type: 'final',
                    approver: card.final_approver,
                    isCurrent: finalIsCurrent,
                    isCompleted: finalIsCompleted,
                    isRejected: finalIsRejected && !finalIsRejectedAt,
                    isRejectedAt: !!finalIsRejectedAt
                  })
                }

                return (
                  <>
                    {/* Горизонтальный таймлайн с полоской */}
                    <div className="relative py-4">
                      <div className="relative flex items-center px-2 overflow-x-auto">
                        {steps.map((step, stepIndex) => {
                          // Определяем цвет кружка
                          let circleClass = ''
                          let icon: React.ReactNode = null

                          if (card.plan_status === 'rejected') {
                            if (step.isRejectedAt) {
                              circleClass = 'bg-red-300 dark:bg-red-700 border-red-400 dark:border-red-600 opacity-60'
                              icon = <X className="w-5 h-5 text-red-700 dark:text-red-300" />
                            } else if (step.isCompleted) {
                              circleClass = 'bg-green-300 dark:bg-green-700 border-green-400 dark:border-green-600 opacity-60'
                              icon = <CheckCircle2 className="w-5 h-5 text-green-700 dark:text-green-300" />
                            } else if (step.isCurrent) {
                              circleClass = 'bg-blue-500 border-blue-600'
                              icon = <Clock className="w-5 h-5 text-white" />
                            } else {
                              circleClass = 'bg-gray-300 dark:bg-gray-600 border-gray-400 dark:border-gray-500 opacity-40'
                              icon = step.type === 'approver' ? (
                                <span className="text-gray-500 dark:text-gray-400 text-sm font-medium">{step.index! + 1}</span>
                              ) : step.type === 'final' ? (
                                <span className="text-gray-500 dark:text-gray-400 text-sm font-medium">✓</span>
                              ) : (
                                <Clock className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                              )
                            }
                          } else if (card.plan_status === 'approved') {
                            circleClass = 'bg-green-500 border-green-600'
                            icon = <CheckCircle2 className="w-5 h-5 text-white" />
                          } else {
                            if (step.isCurrent) {
                              circleClass = 'bg-blue-500 border-blue-600'
                              if (step.type === 'approver') {
                                icon = <span className="text-white text-sm font-bold">{step.index! + 1}</span>
                              } else if (step.type === 'final') {
                                icon = <span className="text-white text-sm font-bold">✓</span>
                              } else {
                                icon = <Clock className="w-5 h-5 text-white" />
                              }
                            } else if (step.isCompleted) {
                              circleClass = 'bg-green-500 border-green-600'
                              icon = <CheckCircle2 className="w-5 h-5 text-white" />
                            } else {
                              circleClass = 'bg-gray-300 dark:bg-gray-600 border-gray-400 dark:border-gray-500 opacity-40'
                              icon = step.type === 'approver' ? (
                                <span className="text-gray-500 dark:text-gray-400 text-sm font-medium">{step.index! + 1}</span>
                              ) : step.type === 'final' ? (
                                <span className="text-gray-500 dark:text-gray-400 text-sm font-medium">✓</span>
                              ) : (
                                <Clock className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                              )
                            }
                          }

                          const label = step.type === 'upload' 
                            ? 'Загрузка плана'
                            : step.type === 'approver'
                            ? step.approver.full_name
                            : step.approver.full_name

                          const statusText = step.isRejectedAt
                            ? 'Отклонено'
                            : step.isCompleted && !step.isRejected
                            ? step.type === 'upload' ? 'Загружено' : step.type === 'final' ? 'Утверждено' : 'Согласовано'
                            : step.isCurrent
                            ? 'Текущий'
                            : 'Ожидает'

                          return (
                            <div key={stepIndex} className="flex flex-col items-center flex-1 min-w-[150px] flex-shrink-0">
                              <div className={`w-16 h-16 rounded-full flex items-center justify-center border-4 z-10 transition-all shadow-md ${circleClass}`}>
                                {icon}
                              </div>
                              <div className="mt-4 text-center w-full">
                                <p className="text-sm font-semibold">{label}</p>
                                <p className={`text-xs mt-1 font-medium ${
                                  step.isRejectedAt 
                                    ? 'text-red-600 dark:text-red-400' 
                                    : step.isCompleted && !step.isRejected
                                    ? 'text-green-600 dark:text-green-400'
                                    : step.isCurrent
                                    ? 'text-blue-600 dark:text-blue-400'
                                    : 'text-muted-foreground'
                                }`}>
                                  {statusText}
                                </p>
                                {step.type === 'upload' && card.plan_submitted_at && (
                                  <p className="text-xs text-muted-foreground mt-1">
                                    {formatDateTimeInAstanaTime(card.plan_submitted_at)}
                                  </p>
                                )}
                                {step.type === 'approver' && step.isCompleted && step.approvalDate && (
                                  <p className="text-xs text-muted-foreground mt-1">
                                    {formatDateTimeInAstanaTime(step.approvalDate)}
                                  </p>
                                )}
                                {step.type === 'final' && card.plan_approved_at && (
                                  <p className="text-xs text-muted-foreground mt-1">
                                    {formatDateTimeInAstanaTime(card.plan_approved_at)}
                                  </p>
                                )}
                                {step.isRejectedAt && rejectedAt && (
                                  <p className="text-xs text-red-600 dark:text-red-400 mt-1 font-medium">
                                    {formatDateTimeInAstanaTime(rejectedAt)}
                                  </p>
                                )}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>

                    {/* Информация об отклонении и форма загрузки исправленного плана */}
                    {card.plan_status === 'rejected' && (
                      <div className="mt-8 space-y-4">
                        {card.plan_rejected_reason && (
                          <div className="p-4 bg-red-50 dark:bg-red-950 rounded-lg border border-red-200 dark:border-red-800">
                            <p className="text-sm font-semibold text-red-700 dark:text-red-300 mb-2">
                              План отклонён
                            </p>
                            <p className="text-sm text-red-600 dark:text-red-400">
                              <strong>Причина:</strong> {card.plan_rejected_reason}
                            </p>
                          </div>
                        )}
                        {canUploadCorrectedPlan && (
                          <div className="p-4 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
                            <p className="text-sm font-semibold text-blue-700 dark:text-blue-300 mb-3">
                              Загрузить исправленный план
                            </p>
                            <div className="space-y-3">
                              <div>
                                <label className="text-sm font-medium mb-2 block">
                                  Файл исправленного плана
                                </label>
                                <div className="flex items-center gap-2">
                                  <Input
                                    type="file"
                                    accept=".pdf,.doc,.docx,.xls,.xlsx"
                                    onChange={(e) => {
                                      const file = e.target.files?.[0] || null
                                      setCorrectedPlanFile(file)
                                    }}
                                    className="flex-1"
                                  />
                                  {correctedPlanFile && (
                                    <span className="text-sm text-muted-foreground">
                                      {correctedPlanFile.name}
                                    </span>
                                  )}
                                </div>
                              </div>
                              <Button
                                onClick={handleUploadCorrectedPlan}
                                disabled={uploadCorrectedPlanMutation.isPending || !correctedPlanFile}
                                className="w-full"
                                variant="default"
                              >
                                <Upload className="w-4 h-4 mr-2" />
                                {uploadCorrectedPlanMutation.isPending ? 'Загрузка...' : 'Загрузить исправленный план'}
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )
              })()}
            </div>
          </DialogContent>
        </Dialog>
      )}
      
      {/* Модальное окно редактирования карточки */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent onClose={() => setShowEditDialog(false)}>
          <DialogHeader>
            <DialogTitle>Редактировать мероприятие</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-description">Описание</Label>
              <Textarea
                id="edit-description"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="Введите описание мероприятия"
                rows={4}
              />
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-start-date">Дата начала</Label>
                <Input
                  id="edit-start-date"
                  type="date"
                  value={editStartDate}
                  onChange={(e) => setEditStartDate(e.target.value)}
                  required
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="edit-end-date">Дата окончания (опционально)</Label>
                <Input
                  id="edit-end-date"
                  type="date"
                  value={editEndDate}
                  onChange={(e) => setEditEndDate(e.target.value)}
                />
              </div>
            </div>
            
            <div className="flex justify-end gap-2 pt-4">
              <Button
                variant="outline"
                onClick={() => setShowEditDialog(false)}
              >
                Отмена
              </Button>
              <Button
                onClick={handleSaveEdit}
                disabled={updateCardMutation.isPending || !editStartDate}
              >
                {updateCardMutation.isPending ? 'Сохранение...' : 'Сохранить'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
