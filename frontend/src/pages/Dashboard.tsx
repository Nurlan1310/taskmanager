import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CheckSquare, Calendar, Users, Clock, AlertCircle, User } from 'lucide-react'
import { Task } from '@/types/task'
import { formatDateTimeInAstanaTime } from '@/lib/dateUtils'

interface DashboardStats {
  total_cards: number
  total_tasks: number
  urgent_tasks: number
  approval_tasks: number
  overdue_tasks: Task[]
  today_tasks: Task[]
  tomorrow_tasks: Task[]
  week_tasks: Task[]
}

// Функция для вычисления просрочки (дни и часы)
function calculateOverdue(dueDate: string): { days: number; hours: number } {
  const due = new Date(dueDate)
  const now = new Date()
  const diffMs = now.getTime() - due.getTime()
  const totalHours = Math.floor(diffMs / (1000 * 60 * 60))
  const days = Math.floor(totalHours / 24)
  const hours = totalHours % 24
  return { days, hours }
}

// Функция для вычисления просрочки (часы и минуты) для колонки "Задачи на сегодня"
function calculateOverdueMinutes(dueDate: string): { hours: number; minutes: number } {
  const due = new Date(dueDate)
  const now = new Date()
  const diffMs = now.getTime() - due.getTime()
  const totalMinutes = Math.floor(diffMs / (1000 * 60))
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return { hours, minutes }
}

// Компонент карточки задачи
function TaskCard({ task, isTodayColumn = false }: { task: Task; isTodayColumn?: boolean }) {
  const isOverdue = task.due_date && new Date(task.due_date) < new Date()
  const overdueInfo = task.due_date && isOverdue 
    ? (isTodayColumn ? calculateOverdueMinutes(task.due_date) : calculateOverdue(task.due_date))
    : null

  // Определяем цвет обводки в зависимости от статуса задачи
  const getBorderColor = () => {
    // Задачи типа review и approval имеют синюю обводку
    if (task.task_type === 'review' || task.task_type === 'approval') {
      return 'border-blue-500'
    }
    
    switch (task.status) {
      case 'new':
        return 'border-gray-500'
      case 'in_progress':
        return 'border-yellow-500'
      case 'done':
        return 'border-green-500'
      case 'rejected':
        return 'border-red-500'
      case 'sent_for_review':
      case 'under_review':
        return 'border-purple-500'
      default:
        return 'border-gray-300'
    }
  }

  return (
    <Link
      to={`/tasks/${task.id}`}
      className={`block p-4 bg-card border-2 ${getBorderColor()} rounded-lg hover:bg-accent hover:shadow-md transition-all cursor-pointer`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="font-semibold text-sm flex-1 line-clamp-2">{task.title}</h3>
      </div>

      <div className="space-y-1 text-xs text-muted-foreground">
        {task.created_by && (
          <div className="flex items-center gap-1">
            <User className="w-3 h-3" />
            <span>
              От: {task.created_by.full_name}
            </span>
          </div>
        )}
        {task.due_date && (
          <div className="flex items-center justify-between gap-1">
            <div className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              <span>{formatDateTimeInAstanaTime(task.due_date)}</span>
            </div>
            {isOverdue && overdueInfo && (
              <Badge variant="destructive" className="flex-shrink-0 whitespace-nowrap text-xs">
                {isTodayColumn ? (
                  // Для колонки "Задачи на сегодня": только часы и минуты (или только минуты)
                  (overdueInfo as { hours: number; minutes: number }).hours > 0 
                    ? `-${(overdueInfo as { hours: number; minutes: number }).hours}ч ${(overdueInfo as { hours: number; minutes: number }).minutes}м`
                    : `-${(overdueInfo as { hours: number; minutes: number }).minutes}м`
                ) : (
                  // Для остальных колонок: дни и часы
                  `-${Math.abs((overdueInfo as { days: number; hours: number }).days)}д -${Math.abs((overdueInfo as { days: number; hours: number }).hours)}ч`
                )}
              </Badge>
            )}
          </div>
        )}
        {task.priority === 'urgent' && (
          <Badge variant="destructive" className="text-xs">
            Срочно
          </Badge>
        )}
      </div>
    </Link>
  )
}

// Компонент колонки
function TaskColumn({ title, tasks, icon: Icon, color, isTodayColumn = false }: { 
  title: string
  tasks: Task[]
  icon: any
  color: string
  isTodayColumn?: boolean
}) {
  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Icon className={`w-5 h-5 ${color}`} />
          <CardTitle className="text-lg">{title}</CardTitle>
          <Badge variant="secondary" className="ml-auto">
            {tasks.length}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto">
        {tasks.length > 0 ? (
          <div className="space-y-3">
            {tasks.map((task) => (
              <TaskCard key={task.id} task={task} isTodayColumn={isTodayColumn} />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground text-sm">
            Нет задач
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const response = await api.get('/dashboard/')
      return response.data
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Дашборд</h1>
        <p className="text-muted-foreground mt-2">
          Планируйте, расставляйте приоритеты и выполняйте задачи с легкостью
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Активных карточек</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_cards || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Доступных для вас мероприятий
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Всего задач</CardTitle>
            <CheckSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_tasks || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Активных задач в работе
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Срочные задачи</CardTitle>
            <Badge variant="destructive">!</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.urgent_tasks || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Требуют немедленного внимания
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">На согласовании</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.approval_tasks || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Ожидают вашего решения
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Task Board */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <TaskColumn
          title="Просроченные задачи"
          tasks={stats?.overdue_tasks || []}
          icon={AlertCircle}
          color="text-red-500"
        />
        <TaskColumn
          title="Задачи на сегодня"
          tasks={stats?.today_tasks || []}
          icon={Clock}
          color="text-blue-500"
          isTodayColumn={true}
        />
        <TaskColumn
          title="Задачи на завтра"
          tasks={stats?.tomorrow_tasks || []}
          icon={Calendar}
          color="text-yellow-500"
        />
        <TaskColumn
          title="Остальные задачи"
          tasks={stats?.week_tasks || []}
          icon={CheckSquare}
          color="text-green-500"
        />
      </div>
    </div>
  )
}
