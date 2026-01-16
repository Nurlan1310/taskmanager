import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import ruLocale from '@fullcalendar/core/locales/ru'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { Task, Employee } from '@/types/task'
import { format } from 'date-fns'
import { User, Filter } from 'lucide-react'
import { formatDateTimeInAstanaTime } from '@/lib/dateUtils'

type TaskScope = 'mine' | 'department' | 'all'

export default function Calendar() {
  const [_currentDate] = useState(new Date())
  const [scopeFilter, setScopeFilter] = useState<TaskScope>('mine')
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(null)

  // Получаем текущего пользователя с полной информацией
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
      return emp.department?.id === userDepartmentId
    }
    return emp.id === currentUser?.employee?.id
  }) || []

  // Сбрасываем выбор сотрудника при смене scope
  useEffect(() => {
    if (scopeFilter !== 'mine' && selectedEmployeeId) {
      setSelectedEmployeeId(null)
    }
  }, [scopeFilter])

  const { data: tasks } = useQuery<Task[]>({
    queryKey: ['tasks', 'calendar', scopeFilter, selectedEmployeeId],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.append('scope', scopeFilter)
      if (selectedEmployeeId) params.append('employee_id', selectedEmployeeId.toString())
      
      const response = await api.get(`/tasks/?${params.toString()}`)
      return Array.isArray(response.data) ? response.data : (response.data.results || [])
    },
  })

  // Преобразуем задачи в события для календаря
  const events = tasks?.map((task) => ({
    id: task.id.toString(),
    title: task.title,
    start: task.due_date || task.created_at,
    end: task.due_date || undefined,
    backgroundColor: 
      task.status === 'done' ? '#22c55e' :
      task.status === 'in_progress' ? '#eab308' :
      task.priority === 'urgent' ? '#ef4444' :
      task.task_type === 'approval' || task.task_type === 'review' ? '#3b82f6' :
      '#6b7280',
    borderColor: 
      task.status === 'done' ? '#16a34a' :
      task.status === 'in_progress' ? '#ca8a04' :
      task.priority === 'urgent' ? '#dc2626' :
      task.task_type === 'approval' || task.task_type === 'review' ? '#2563eb' :
      '#4b5563',
    extendedProps: {
      taskId: task.id,
      status: task.status,
      taskType: task.task_type,
      title: task.title,
      due_date: task.due_date,
      created_by: task.created_by,
      assigned_employee: task.assigned_employee,
    },
  })) || []

  // Очищаем все tooltip при изменении событий
  useEffect(() => {
    return () => {
      // Удаляем все tooltip при размонтировании или изменении событий
      const tooltips = document.querySelectorAll('.calendar-tooltip')
      tooltips.forEach(tooltip => {
        if (tooltip.parentNode) {
          tooltip.parentNode.removeChild(tooltip)
        }
      })
    }
  }, [events])

  // Функция для форматирования времени из даты
  const formatTime = (dateStr: string | undefined) => {
    if (!dateStr) return ''
    try {
      const date = new Date(dateStr)
      return format(date, 'HH:mm')
    } catch {
      return ''
    }
  }

  // Кастомное отображение события - только время
  const eventContent = (arg: any) => {
    try {
      const timeStr = formatTime(arg.event.startStr)
      // Для месячного и недельного вида показываем только время
      if (arg.view.type === 'dayGridMonth' || arg.view.type === 'timeGridWeek') {
        return {
          html: `<div class="fc-event-time" style="font-weight: 500;">${timeStr}</div>`,
        }
      }
      // Для дневного вида показываем название
      return {
        html: `<div class="fc-event-title">${arg.event.title}</div>`,
      }
    } catch (error) {
      console.error('Error in eventContent:', error)
      // Возвращаем стандартное отображение при ошибке
      return undefined
    }
  }

  // Создаем tooltip при наведении
  const handleEventDidMount = (arg: any) => {
    try {
      const eventEl = arg.el
      const taskData = arg.event.extendedProps
      
      if (!eventEl || !taskData) {
        return
      }

    // Создаем tooltip элемент
    const tooltip = document.createElement('div')
    tooltip.className = 'calendar-tooltip'
    tooltip.style.cssText = `
      position: absolute;
      background: #1f2937;
      color: white;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12px;
      z-index: 10000;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.2s;
      max-width: 250px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    `

    // Формируем содержимое tooltip
    let tooltipContent = `<div style="font-weight: 600; margin-bottom: 4px;">${taskData.title || 'Задача'}</div>`
    
    if (taskData.due_date) {
      tooltipContent += `<div style="margin-bottom: 2px;">Срок: ${formatDateTimeInAstanaTime(taskData.due_date)}</div>`
    }
    
    if (taskData.created_by) {
      const creatorName = `${taskData.created_by.user?.first_name || ''} ${taskData.created_by.user?.last_name || ''}`.trim()
      if (creatorName) {
        tooltipContent += `<div style="margin-bottom: 2px;">От: ${creatorName}</div>`
      }
    }
    
    if (scopeFilter === 'department' && taskData.assigned_employee) {
      const assigneeName = `${taskData.assigned_employee.user?.first_name || ''} ${taskData.assigned_employee.user?.last_name || ''}`.trim()
      if (assigneeName) {
        tooltipContent += `<div>Исполнитель: ${assigneeName}</div>`
      }
    }

    tooltip.innerHTML = tooltipContent

    // Добавляем tooltip в body для правильного позиционирования
    document.body.appendChild(tooltip)

    let showTimeout: NodeJS.Timeout
    let hideTimeout: NodeJS.Timeout

    const showTooltip = (_e: MouseEvent) => {
      clearTimeout(hideTimeout)
      showTimeout = setTimeout(() => {
        tooltip.style.opacity = '1'
        const rect = eventEl.getBoundingClientRect()
        const tooltipRect = tooltip.getBoundingClientRect()
        
        // Позиционируем tooltip над событием
        let top = rect.top - tooltipRect.height - 8
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2)
        
        // Если tooltip выходит за верхний край экрана, показываем снизу
        if (top < 10) {
          top = rect.bottom + 8
        }
        
        // Если tooltip выходит за левый край, выравниваем по левому краю события
        if (left < 10) {
          left = rect.left
        }
        
        // Если tooltip выходит за правый край, выравниваем по правому краю события
        if (left + tooltipRect.width > window.innerWidth - 10) {
          left = rect.right - tooltipRect.width
        }
        
        tooltip.style.top = `${top + window.scrollY}px`
        tooltip.style.left = `${left + window.scrollX}px`
      }, 300) // Небольшая задержка перед показом
    }

    const hideTooltip = () => {
      clearTimeout(showTimeout)
      hideTimeout = setTimeout(() => {
        tooltip.style.opacity = '0'
      }, 100)
    }

    const moveHandler = (_e: MouseEvent) => {
      if (tooltip.style.opacity === '1') {
        const rect = eventEl.getBoundingClientRect()
        const tooltipRect = tooltip.getBoundingClientRect()
        
        let top = rect.top - tooltipRect.height - 8
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2)
        
        if (top < 10) {
          top = rect.bottom + 8
        }
        if (left < 10) {
          left = rect.left
        }
        if (left + tooltipRect.width > window.innerWidth - 10) {
          left = rect.right - tooltipRect.width
        }
        
        tooltip.style.top = `${top + window.scrollY}px`
        tooltip.style.left = `${left + window.scrollX}px`
      }
    }

    eventEl.addEventListener('mouseenter', showTooltip)
    eventEl.addEventListener('mouseleave', hideTooltip)
    eventEl.addEventListener('mousemove', moveHandler)

    // Очистка при удалении события
    const cleanup = () => {
      clearTimeout(showTimeout)
      clearTimeout(hideTimeout)
      eventEl.removeEventListener('mouseenter', showTooltip)
      eventEl.removeEventListener('mouseleave', hideTooltip)
      eventEl.removeEventListener('mousemove', moveHandler)
      if (tooltip.parentNode) {
        tooltip.parentNode.removeChild(tooltip)
      }
    }

      // Сохраняем функцию очистки в элементе события для последующего использования
      ;(eventEl as any).__tooltipCleanup = cleanup

      return cleanup
    } catch (error) {
      console.error('Error in handleEventDidMount:', error)
      return undefined
    }
  }

  const handleDateClick = (arg: any) => {
    console.log('Date clicked:', arg.dateStr)
    // Можно открыть модальное окно для создания задачи на эту дату
  }

  const handleEventClick = (arg: any) => {
    const taskId = arg.event.extendedProps.taskId
    if (taskId) {
      window.location.href = `/tasks/${taskId}`
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Календарь</h1>
        <p className="text-muted-foreground mt-2">
          Просмотр задач в календарном виде
        </p>
      </div>

      {/* Фильтры */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Фильтры</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Фильтр по области видимости */}
          <div>
            <label className="text-sm font-medium mb-2 block">Область видимости</label>
            <div className="flex flex-wrap gap-2">
              <Button
                variant={scopeFilter === 'mine' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setScopeFilter('mine')}
              >
                <User className="w-4 h-4 mr-2" />
                Мои задачи
              </Button>
              <Button
                variant={scopeFilter === 'department' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setScopeFilter('department')}
              >
                <Filter className="w-4 h-4 mr-2" />
                Задачи моего отдела
              </Button>
              {canViewAll && (
                <Button
                  variant={scopeFilter === 'all' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setScopeFilter('all')}
                >
                  <Filter className="w-4 h-4 mr-2" />
                  Все задачи
                </Button>
              )}
            </div>
          </div>

          {/* Выбор сотрудника (для руководителя и директора) */}
          {(isHead || canViewAll) && scopeFilter !== 'mine' && (
            <div>
              <label className="text-sm font-medium mb-2 block">Выбрать сотрудника (необязательно)</label>
              <Select
                value={selectedEmployeeId?.toString() || ''}
                onChange={(e) => setSelectedEmployeeId(e.target.value ? parseInt(e.target.value) : null)}
              >
                <option value="">Все сотрудники</option>
                {availableEmployees.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.user.first_name} {emp.user.last_name}
                    {emp.position && ` (${emp.position})`}
                    {emp.department && ` - ${emp.department.name}`}
                  </option>
                ))}
              </Select>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <FullCalendar
            plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
            initialView="dayGridMonth"
            headerToolbar={{
              left: 'prev,next today',
              center: 'title',
              right: 'dayGridMonth,timeGridWeek,timeGridDay',
            }}
            events={events}
            dateClick={handleDateClick}
            eventClick={handleEventClick}
            locale={ruLocale}
            firstDay={1}
            height="auto"
            eventDisplay="block"
            dayMaxEvents={3}
            moreLinkClick="popover"
            eventContent={eventContent}
            eventDidMount={handleEventDidMount}
            eventTimeFormat={{
              hour: '2-digit',
              minute: '2-digit',
              meridiem: false,
            }}
            slotLabelFormat={{
              hour: '2-digit',
              minute: '2-digit',
              meridiem: false,
            }}
            views={{
              dayGridMonth: {
                allDaySlot: false,
              },
              timeGridWeek: {
                allDaySlot: false,
                slotMinTime: '08:00:00',
              },
              timeGridDay: {
                allDaySlot: false,
                slotMinTime: '08:00:00',
              },
            }}
          />
        </CardContent>
      </Card>

      {/* Легенда */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-green-500"></div>
              <span>Выполненные</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-yellow-500"></div>
              <span>В работе</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-red-500"></div>
              <span>Срочные</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-blue-500"></div>
              <span>На согласовании</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-gray-500"></div>
              <span>Остальные</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

