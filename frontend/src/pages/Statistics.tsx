import { useState, useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuthStore } from '@/store/authStore'
import { Employee } from '@/types/task'
import { 
  BarChart3, 
  CheckSquare, 
  Calendar, 
  TrendingUp, 
  Filter,
  RefreshCw
} from 'lucide-react'
import { formatDateInAstanaTime } from '@/lib/dateUtils'
import PieChart from '@/components/PieChart'
import SearchableSelect from '@/components/SearchableSelect'

interface Department {
  id: number
  name: string
}

interface EventCard {
  id: number
  title: string
  start_date: string
  end_date?: string
}

interface StatisticsData {
  period: {
    from: string
    to: string
  }
  tasks: {
    total: number
    by_status: Record<string, number>
    by_type: Record<string, number>
    by_priority: Record<string, number>
    done: number
    in_progress: number
    new: number
  }
  events: {
    total: number
  }
}

const STATUS_LABELS: Record<string, string> = {
  new: 'Новые',
  in_progress: 'В работе',
  done: 'Выполнены',
  rejected: 'Отклонены',
  sent_for_review: 'На согласовании',
  under_review: 'На рассмотрении',
}

const TYPE_LABELS: Record<string, string> = {
  regular: 'Обычные',
  approval: 'Согласование',
  review: 'Проверка',
}

const PRIORITY_LABELS: Record<string, string> = {
  normal: 'Обычная',
  urgent: 'Срочная',
}

// Цвета для статусов
const STATUS_COLORS: Record<string, string> = {
  new: '#94a3b8', // slate-400
  in_progress: '#fbbf24', // amber-400
  done: '#22c55e', // green-500
  rejected: '#ef4444', // red-500
  sent_for_review: '#a855f7', // purple-500
  under_review: '#3b82f6', // blue-500
}

// Цвета для типов
const TYPE_COLORS: Record<string, string> = {
  regular: '#3b82f6', // blue-500
  approval: '#f59e0b', // amber-500
  review: '#8b5cf6', // violet-500
}

// Цвета для приоритетов
const PRIORITY_COLORS: Record<string, string> = {
  normal: '#6b7280', // gray-500
  urgent: '#ef4444', // red-500
}

export default function Statistics() {
  const { user } = useAuthStore()
  const [searchParams] = useSearchParams()
  const userRole = user?.employee?.role
  const userDepartmentId = user?.employee?.department?.id
  const userId = user?.employee?.id
  
  const isDirectorOrDeputy = userRole === 'director' || userRole === 'deputy'
  const isHead = userRole === 'head'
  const isRegular = !isDirectorOrDeputy && !isHead
  
  // State для фильтров
  const [filterMode, setFilterMode] = useState<'dates' | 'event'>('dates') // 'dates' или 'event'
  const [selectedDepartmentId, setSelectedDepartmentId] = useState<string>('')
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>('')
  const [selectedCardId, setSelectedCardId] = useState<string>('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [isManualLoading, setIsManualLoading] = useState(false)
  
  // Инициализация из URL параметров и дефолтных значений
  useEffect(() => {
    const cardIdFromUrl = searchParams.get('card_id')
    const departmentIdFromUrl = searchParams.get('department_id')
    const employeeIdFromUrl = searchParams.get('employee_id')
    const filterModeFromUrl = searchParams.get('filter_mode')
    
    // Устанавливаем значения из URL, если они есть
    if (cardIdFromUrl) {
      setSelectedCardId(cardIdFromUrl)
      if (filterModeFromUrl === 'event') {
        setFilterMode('event')
      }
    }
    
    if (departmentIdFromUrl) {
      setSelectedDepartmentId(departmentIdFromUrl)
    } else if (userDepartmentId) {
      // Если нет в URL, устанавливаем дефолтное значение
      setSelectedDepartmentId(userDepartmentId.toString())
    }
    
    if (employeeIdFromUrl !== null) {
      // Если параметр явно указан в URL (даже если пустой), используем его
      setSelectedEmployeeId(employeeIdFromUrl)
    } else if (userId && !departmentIdFromUrl) {
      // Если нет параметра в URL и не указан отдел, устанавливаем дефолтное значение
      setSelectedEmployeeId(userId.toString())
    }
  }, [searchParams, userDepartmentId, userId])
  
  // Функция для форматирования даты в YYYY-MM-DD (локальное время, без проблем с часовым поясом)
  const formatDateLocal = (date: Date): string => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  
  // Функция для установки дефолтных дат (текущий месяц)
  const setDefaultDates = useCallback(() => {
    const today = new Date()
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0)
    
    setDateFrom(formatDateLocal(firstDay))
    setDateTo(formatDateLocal(lastDay))
  }, [])
  
  // Инициализация дат (текущий месяц по умолчанию)
  useEffect(() => {
    setDefaultDates()
  }, [])
  
  // Загрузка отделов
  const { data: departments } = useQuery<Department[]>({
    queryKey: ['departments'],
    queryFn: async () => {
      const response = await api.get('/departments/')
      return Array.isArray(response.data) ? response.data : (response.data.results || [])
    },
  })
  
  // Загрузка сотрудников отдела
  const { data: employees } = useQuery<Employee[]>({
    queryKey: ['employees', selectedDepartmentId],
    queryFn: async () => {
      const response = await api.get('/employees/')
      const allEmployees = Array.isArray(response.data) ? response.data : (response.data.results || [])
      if (selectedDepartmentId) {
        return allEmployees.filter((emp: Employee) => emp.department?.id === parseInt(selectedDepartmentId))
      }
      return allEmployees
    },
    enabled: true,
  })
  
  // Загрузка мероприятий (активные и архивные, включая категорию "внутренняя работа")
  const { data: cards } = useQuery<EventCard[]>({
    queryKey: ['cards', 'all', 'statistics'],
    queryFn: async () => {
      // Загружаем все категории мероприятий для статистики
      // Используем параметр category=all чтобы получить все категории (включая внутреннюю работу)
      // Но если API не поддерживает category=all, делаем запросы с конкретными категориями
      
      // Сначала получаем все мероприятия без фильтра по категории
      // Для этого делаем запросы с архивными и активными, но нужно обойти фильтр категории
      // Попробуем передать category как пустую строку или специальное значение
      
      // Загружаем активные мероприятия (используем include_all=true чтобы получить все категории)
      const activeResponse = await api.get('/cards/?archive=false&include_all=true')
      const activeCards = Array.isArray(activeResponse.data) 
        ? activeResponse.data 
        : (activeResponse.data.results || [])
      
      // Загружаем архивные мероприятия
      const archiveResponse = await api.get('/cards/?archive=true&include_all=true')
      const archiveCards = Array.isArray(archiveResponse.data)
        ? archiveResponse.data
        : (archiveResponse.data.results || [])
      
      // Объединяем и убираем дубликаты по id
      const allCards = [...activeCards, ...archiveCards]
      const uniqueCards = allCards.filter((card, index, self) => 
        index === self.findIndex((c) => c.id === card.id)
      )
      
      return uniqueCards
    },
    enabled: true,
  })
  
  // Состояние для данных статистики
  const [statistics, setStatistics] = useState<StatisticsData | null>(null)
  
  // Выбранное мероприятие для получения его дат
  const selectedCard = cards?.find(card => card.id.toString() === selectedCardId)
  
  // Сброс/установка сотрудника при изменении отдела
  useEffect(() => {
    if (!selectedDepartmentId) {
      // Если выбран "Все отделы", сбрасываем сотрудника
      setSelectedEmployeeId('')
    } else if (selectedDepartmentId === userDepartmentId?.toString()) {
      // Если выбран свой отдел, устанавливаем себя по умолчанию (если сотрудник не выбран)
      if (!selectedEmployeeId && userId) {
        setSelectedEmployeeId(userId.toString())
      }
    } else {
      // Если выбран другой отдел, сбрасываем сотрудника
      setSelectedEmployeeId('')
    }
  }, [selectedDepartmentId, userDepartmentId])
  
  // Обработка изменения режима фильтрации
  useEffect(() => {
    if (filterMode === 'dates') {
      // При выборе режима по датам, сбрасываем мероприятие и устанавливаем дефолтные даты
      setSelectedCardId('')
      setDefaultDates()
    }
  }, [filterMode, setDefaultDates])
  
  // При выборе мероприятия, переключаемся в режим мероприятия и устанавливаем даты
  useEffect(() => {
    if (selectedCardId && cards) {
      const card = cards.find(card => card.id.toString() === selectedCardId)
      if (card) {
        if (filterMode === 'dates') {
          setFilterMode('event')
        }
        // Устанавливаем даты мероприятия
        const startDate = new Date(card.start_date)
        setDateFrom(formatDateLocal(startDate))
        if (card.end_date) {
          const endDate = new Date(card.end_date)
          setDateTo(formatDateLocal(endDate))
        } else {
          setDateTo(formatDateLocal(startDate))
        }
      }
    }
  }, [selectedCardId, cards])
  
  const handleApplyFilters = async () => {
    // Проверяем валидность данных перед запросом
    if (!dateFrom || !dateTo) {
      return
    }
    if (filterMode === 'event' && !selectedCardId) {
      return
    }
    
    // Построение параметров запроса
    const queryParams = new URLSearchParams()
    if (dateFrom) queryParams.set('date_from', dateFrom)
    if (dateTo) queryParams.set('date_to', dateTo)
    if (filterMode === 'event' && selectedCardId) {
      queryParams.set('card_id', selectedCardId)
    }
    if (selectedDepartmentId) queryParams.set('department_id', selectedDepartmentId)
    if (selectedEmployeeId) queryParams.set('employee_id', selectedEmployeeId)
    
    setIsManualLoading(true)
    try {
      const response = await api.get(`/statistics/?${queryParams.toString()}`)
      setStatistics(response.data)
    } catch (error) {
      console.error('Error fetching statistics:', error)
      setStatistics(null)
    } finally {
      setIsManualLoading(false)
    }
  }
  
  const progressPercentage = statistics?.tasks.total 
    ? Math.round((statistics.tasks.done / statistics.tasks.total) * 100)
    : 0
  
  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <BarChart3 className="w-8 h-8" />
            Статистика
          </h1>
          <p className="text-muted-foreground mt-2">
            Аналитика по задачам и мероприятиям
          </p>
        </div>
      </div>
      
      {/* Фильтры */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Фильтры
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Первая строка: Отдел и Сотрудник */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Отдел */}
              <div className="space-y-2">
                <Label>Отдел</Label>
                <Select
                  value={selectedDepartmentId}
                  onChange={(e) => setSelectedDepartmentId(e.target.value)}
                  disabled={isHead || isRegular}
                >
                  {isDirectorOrDeputy && (
                    <option value="">Все отделы</option>
                  )}
                  {departments?.map((dept) => (
                    <option key={dept.id} value={dept.id.toString()}>
                      {dept.name}
                    </option>
                  ))}
                </Select>
              </div>
              
              {/* Сотрудник */}
              <div className="space-y-2">
                <Label>Сотрудник</Label>
                <SearchableSelect
                  options={[
                    { value: '', label: 'Все сотрудники отдела' },
                    ...(employees?.map((emp) => ({
                      value: emp.id.toString(),
                      label: emp.full_name || `${emp.user.first_name} ${emp.user.last_name}` || 'Без имени'
                    })) || [])
                  ]}
                  value={selectedEmployeeId}
                  onChange={(value) => setSelectedEmployeeId(value)}
                  placeholder="Все сотрудники отдела"
                  disabled={isRegular}
                  emptyText="Нет сотрудников"
                />
              </div>
            </div>
            
            {/* Переключатель режима */}
            <div className="flex items-center gap-4">
              <Label>Период:</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant={filterMode === 'dates' ? 'default' : 'outline'}
                  onClick={() => setFilterMode('dates')}
                  size="sm"
                >
                  По датам
                </Button>
                <Button
                  type="button"
                  variant={filterMode === 'event' ? 'default' : 'outline'}
                  onClick={() => setFilterMode('event')}
                  size="sm"
                >
                  По мероприятию
                </Button>
              </div>
            </div>
            
            {/* Вторая строка: Даты */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Дата от */}
              <div className="space-y-2">
                <Label>Дата от</Label>
                {filterMode === 'dates' ? (
                  <Input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                  />
                ) : (
                  <Input
                    type="date"
                    value={dateFrom}
                    disabled
                    className="bg-muted"
                  />
                )}
              </div>
              
              {/* Дата до */}
              <div className="space-y-2">
                <Label>Дата до</Label>
                {filterMode === 'dates' ? (
                  <Input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                  />
                ) : (
                  <Input
                    type="date"
                    value={dateTo}
                    disabled
                    className="bg-muted"
                  />
                )}
              </div>
            </div>
            
            {/* Третья строка: Мероприятие */}
            <div className="grid grid-cols-1 gap-4">
              <div className="space-y-2">
                <Label>Мероприятие</Label>
                <SearchableSelect
                  options={[
                    { value: '', label: 'Все мероприятия' },
                    ...(cards?.map((card) => ({
                      value: card.id.toString(),
                      label: card.title
                    })) || [])
                  ]}
                  value={selectedCardId}
                  onChange={(value) => setSelectedCardId(value)}
                  placeholder="Все мероприятия"
                  disabled={filterMode === 'dates'}
                  emptyText="Нет мероприятий"
                />
                {filterMode === 'event' && selectedCard && (
                  <div className="text-sm text-muted-foreground mt-1">
                    Период мероприятия: {formatDateInAstanaTime(selectedCard.start_date)}
                    {selectedCard.end_date && ` — ${formatDateInAstanaTime(selectedCard.end_date)}`}
                  </div>
                )}
              </div>
            </div>
            
            {/* Кнопка применения */}
            <div className="flex justify-end">
              <Button 
                onClick={handleApplyFilters}
                disabled={isManualLoading || !dateFrom || !dateTo || (filterMode === 'event' && !selectedCardId)}
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${isManualLoading ? 'animate-spin' : ''}`} />
                Применить фильтры
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Период */}
      {statistics && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Calendar className="w-4 h-4" />
              <span>
                Период: {formatDateInAstanaTime(statistics.period.from)} — {formatDateInAstanaTime(statistics.period.to)}
              </span>
            </div>
          </CardContent>
        </Card>
      )}
      
      {isManualLoading ? (
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="flex flex-col items-center gap-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            <p className="text-muted-foreground">Загрузка статистики...</p>
          </div>
        </div>
      ) : statistics ? (
        <>
          {/* Основная статистика */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Всего задач</CardTitle>
                <CheckSquare className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{statistics.tasks.total}</div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Выполнено</CardTitle>
                <TrendingUp className="h-4 w-4 text-green-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">{statistics.tasks.done}</div>
                <p className="text-xs text-muted-foreground">
                  {progressPercentage}% от общего числа
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">В работе</CardTitle>
                <RefreshCw className="h-4 w-4 text-yellow-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-yellow-600">{statistics.tasks.in_progress}</div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Мероприятий</CardTitle>
                <Calendar className="h-4 w-4 text-blue-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600">{statistics.events.total}</div>
              </CardContent>
            </Card>
          </div>
          
          {/* Прогресс выполнения */}
          {statistics.tasks.total > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Прогресс выполнения</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span>Выполнено</span>
                    <span className="font-semibold">
                      {statistics.tasks.done} / {statistics.tasks.total} ({progressPercentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-4">
                    <div
                      className="bg-green-600 rounded-full h-4 transition-all flex items-center justify-end pr-2"
                      style={{ width: `${progressPercentage}%` }}
                    >
                      {progressPercentage > 10 && (
                        <span className="text-xs text-white font-semibold">{progressPercentage}%</span>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
          
          {/* Статистика по статусам, типам и приоритетам */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {Object.keys(statistics.tasks.by_status).length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Задачи по статусам</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex justify-center">
                    <PieChart
                      data={Object.entries(statistics.tasks.by_status).map(([status, count]) => ({
                        label: STATUS_LABELS[status] || status,
                        value: count,
                        color: STATUS_COLORS[status] || '#94a3b8'
                      }))}
                      total={statistics.tasks.total}
                      size={250}
                    />
                  </div>
                </CardContent>
              </Card>
            )}
            
            {Object.keys(statistics.tasks.by_type).length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Задачи по типам</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex justify-center">
                    <PieChart
                      data={Object.entries(statistics.tasks.by_type).map(([type, count]) => ({
                        label: TYPE_LABELS[type] || type,
                        value: count,
                        color: TYPE_COLORS[type] || '#3b82f6'
                      }))}
                      total={statistics.tasks.total}
                      size={250}
                    />
                  </div>
                </CardContent>
              </Card>
            )}
            
            {Object.keys(statistics.tasks.by_priority).length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Задачи по приоритетам</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex justify-center">
                    <PieChart
                      data={Object.entries(statistics.tasks.by_priority).map(([priority, count]) => ({
                        label: PRIORITY_LABELS[priority] || priority,
                        value: count,
                        color: PRIORITY_COLORS[priority] || '#6b7280'
                      }))}
                      total={statistics.tasks.total}
                      size={250}
                    />
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Выберите фильтры и нажмите "Применить фильтры"</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
