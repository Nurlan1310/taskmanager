import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { useSearchStore } from '@/store/searchStore'
import { DndContext, DragEndEvent, closestCenter } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import api from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
// import { Select } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Task, TaskStatus, Employee } from '@/types/task'
import SearchableSelect from '@/components/SearchableSelect'
import { 
  Plus, 
  Filter, 
  GripVertical, 
  Calendar, 
  User, 
  Clock,
  CheckCircle2,
  Circle,
  AlertCircle,
  FileText,
  ChevronLeft,
  ChevronRight,
  XCircle,
  ArrowRight
} from 'lucide-react'
import { formatDateTimeInAstanaTime, formatDateInAstanaTime } from '@/lib/dateUtils'

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

function TaskItem({ task }: { task: Task }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id.toString() })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  const isUrgent = task.due_date && new Date(task.due_date) <= new Date(Date.now() + 3 * 24 * 60 * 60 * 1000)

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="bg-card border rounded-lg p-4 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start gap-3">
        <div
          {...attributes}
          {...listeners}
          className="cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground"
        >
          <GripVertical className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <Link
              to={`/tasks/${task.id}`}
              className="font-semibold text-lg hover:text-primary transition-colors truncate flex-1 min-w-0"
            >
              {task.title}
            </Link>
            <div className="flex items-center gap-2 flex-shrink-0 whitespace-nowrap">
              {task.priority === 'urgent' && (
                <Badge variant="destructive" className="whitespace-nowrap">
                  <AlertCircle className="w-3 h-3 mr-1" />
                  Срочно
                </Badge>
              )}
              {(task.task_type === 'approval' || task.task_type === 'review') && (
                <Badge variant="default" className="bg-blue-500 whitespace-nowrap">
                  {task.task_type === 'approval' ? 'Согласование' : 'Проверка'}
                </Badge>
              )}
              <Badge className={`${statusColors[task.status]} whitespace-nowrap`}>
                {statusLabels[task.status]}
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
                  {task.redirect_chain_employees && task.redirect_chain_employees.length > 0 && (
                    <>
                      <ArrowRight className="w-3 h-3" />
                      <span className="text-muted-foreground">
                        {task.redirect_chain_employees.map(emp => emp.full_name).join(' → ')}
                      </span>
                    </>
                  )}
                  {(task.status === 'sent_for_review' || task.status === 'under_review') && task.current_reviewer && (
                    <>
                      <span className="mx-1">|</span>
                      <User className="w-4 h-4" />
                      <span>
                        Проверяет: {task.current_reviewer.full_name}
                      </span>
                    </>
                  )}
                  {(task.status === 'send_for_approve' || task.status === 'pending' || task.status === 'in_progress') && task.current_approver && (
                    <>
                      <span className="mx-1">|</span>
                      <User className="w-4 h-4" />
                      <span>
                        Согласует: {task.current_approver.full_name}
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
                    to={`/cards/${task.card}`}
                    className="text-primary hover:underline"
                  >
                    {task.card_title}
                  </Link>
                </div>
              )}
              {task.assigned_employee && (
                <div className="flex items-center gap-1">
                  <User className="w-4 h-4" />
                  <span className="font-bold">
                    Исполнитель: {task.assigned_employee.full_name}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

interface EventCard {
  id: number
  title: string
  start_date: string
  end_date?: string
  is_active?: boolean
  visible?: boolean
  has_plan?: boolean
  plan_status?: 'draft' | 'pending' | 'rejected' | 'approved'
}

const ASSIGNMENTS_PER_PAGE = 30

export default function Assignments() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all')
  const [selectedAssigneeId, setSelectedAssigneeId] = useState<string>('')
  const [currentPage, setCurrentPage] = useState(1)
  const [showCardModal, setShowCardModal] = useState(false)
  const [cardSearchQuery, setCardSearchQuery] = useState('')
  const { query, setQuery } = useSearchStore()

  // Синхронизация с URL параметрами
  useEffect(() => {
    const searchQuery = searchParams.get('search')
    if (searchQuery) {
      setQuery(searchQuery)
    }
  }, [searchParams, setQuery])

  // Сброс страницы при изменении фильтров
  useEffect(() => {
    setCurrentPage(1)
  }, [statusFilter, selectedAssigneeId, query])

  // Список сотрудников для фильтра «Исполнитель»
  const { data: employees } = useQuery<Employee[]>({
    queryKey: ['employees'],
    queryFn: async () => {
      const response = await api.get('/employees/')
      const allEmployees = Array.isArray(response.data)
        ? response.data
        : (response.data.results || [])

      // Исключаем сотрудников без отдела
      return allEmployees.filter((emp: Employee) => !!emp.department)
    },
  })

  // Получаем активные мероприятия для модального окна
  const { data: activeCards } = useQuery<EventCard[]>({
    queryKey: ['activeCards', 'forTaskCreation'],
    queryFn: async () => {
      const response = await api.get('/cards/?archive=false&include_all=true')
      const allCards = Array.isArray(response.data) ? response.data : (response.data.results || [])
      // Фильтруем только активные мероприятия, где можно создавать задачи
      return allCards.filter((card: EventCard) => {
        // Активное мероприятие: is_active=true и (visible=true или нет плана или план утвержден)
        return card.is_active && (card.visible || !card.has_plan || card.plan_status === 'approved')
      })
    },
    enabled: showCardModal, // Загружаем только когда модальное окно открыто
  })

  const handleCardSelect = (cardId: number) => {
    navigate(`/cards/${cardId}/tasks/new`)
  }

  // Фильтруем мероприятия по поисковому запросу
  const filteredCards = activeCards?.filter((card) =>
    card.title.toLowerCase().includes(cardSearchQuery.toLowerCase())
  ) || []

  const { data: tasksData, isLoading, refetch } = useQuery<{
    results: Task[]
    count: number
    next: string | null
    previous: string | null
  }>({
    queryKey: ['assignments', statusFilter, query, selectedAssigneeId, currentPage],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.append('scope', 'assignments')
      if (statusFilter !== 'all') params.append('status', statusFilter)
      if (query) params.append('search', query)
      if (selectedAssigneeId) params.append('employee_id', selectedAssigneeId)
      params.append('page', currentPage.toString())

      const response = await api.get(`/tasks/?${params.toString()}`)

      if (Array.isArray(response.data)) {
        const regular = response.data.filter((task: Task) => task.task_type === 'regular')
        return {
          results: regular,
          count: regular.length,
          next: null,
          previous: null,
        }
      }

      const allTasks = response.data.results || []
      const regular = allTasks.filter((task: Task) => task.task_type === 'regular')
      return {
        results: regular,
        count: response.data.count ?? regular.length,
        next: response.data.next ?? null,
        previous: response.data.previous ?? null,
      }
    },
  })

  const tasks = tasksData?.results ?? []
  const totalCount = tasksData?.count ?? 0
  const hasNext = !!tasksData?.next
  const hasPrevious = !!tasksData?.previous
  const totalPages = Math.ceil(totalCount / ASSIGNMENTS_PER_PAGE) || 1

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return

    const taskId = parseInt(active.id.toString())
    const task = tasks?.find(t => t.id === taskId)
    if (!task) return

    // Если перетаскиваем в другую колонку статуса
    const statusColumns = ['new', 'in_progress', 'under_review', 'done']
    if (statusColumns.includes(over.id.toString())) {
      const newStatus = over.id.toString() as TaskStatus
      if (task.status !== newStatus) {
        try {
          await api.patch(`/tasks/${taskId}/`, { status: newStatus })
          refetch()
        } catch (error) {
          console.error('Failed to update task status:', error)
        }
      }
    }
  }

  const statusColumns: { id: TaskStatus | 'all'; label: string; icon: any }[] = [
    { id: 'all', label: 'Активные', icon: Filter },
    { id: 'new', label: 'Новые', icon: Circle },
    { id: 'in_progress', label: 'В работе', icon: Clock },
    { id: 'under_review', label: 'На проверке', icon: FileText },
    { id: 'rejected', label: 'Отклоненные', icon: XCircle },
    { id: 'done', label: 'Выполненные', icon: CheckCircle2 },
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Поручения</h1>
          <p className="text-muted-foreground mt-2">
            Задачи, которые вы создали и поручили другим
          </p>
        </div>
        <Button onClick={() => setShowCardModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Создать задачу
        </Button>
      </div>

      {/* Фильтры */}
      <Card>
        <CardContent className="p-4 space-y-3">
          {/* Первая строка: Статус и переключатель страниц */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">Статус:</span>
              <div className="flex flex-wrap gap-1">
                {statusColumns.map((col) => {
                  const Icon = col.icon
                  return (
                    <Button
                      key={col.id}
                      variant={statusFilter === col.id ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setStatusFilter(col.id as any)}
                      className="h-8 px-2 text-xs"
                    >
                      <Icon className="w-3 h-3 mr-1" />
                      {col.label}
                    </Button>
                  )
                })}
              </div>
            </div>

            {/* Переключатель страниц */}
            {totalPages > 1 && (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={!hasPrevious}
                  className="h-8 px-2"
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                  Страница {currentPage} из {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={!hasNext}
                  className="h-8 px-2"
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            )}
          </div>

          {/* Вторая строка: Исполнитель */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">Исполнитель:</span>
              <div className="min-w-[320px]">
                <SearchableSelect
                  options={[
                    { value: '', label: 'Все сотрудники' },
                    ...(employees ?? []).map((emp) => ({
                      value: emp.id.toString(),
                      label:
                        emp.full_name ??
                        ([emp.firstname, emp.lastname].filter(Boolean).join(' ') || `Сотрудник ${emp.id}`) +
                        (emp.position ? ` (${emp.position})` : ''),
                    })),
                  ]}
                  value={selectedAssigneeId}
                  onChange={(value) => {
                    setSelectedAssigneeId(value)
                    setCurrentPage(1)
                  }}
                  placeholder="Все сотрудники"
                  emptyText="Нет сотрудников"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Список задач */}
      {tasks && tasks.length > 0 ? (
        <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={tasks.map(t => t.id.toString())} strategy={verticalListSortingStrategy}>
            <div className="space-y-3">
              {tasks.map((task) => (
                <TaskItem key={task.id} task={task} />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Нет поручений для отображения</p>
          </CardContent>
        </Card>
      )}

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
                      onClick={() => handleCardSelect(card.id)}
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
