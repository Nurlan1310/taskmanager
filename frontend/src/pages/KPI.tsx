import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import { Employee } from '@/types/task'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import SearchableSelect from '@/components/SearchableSelect'
import { BarChart3, Filter, RefreshCw, Award, Shield } from 'lucide-react'
import { toast } from 'sonner'

interface Department {
  id: number
  name: string
  priority?: number
}

interface KPIReport {
  id: number
  year: number
  month: number
  generated_at: string
  formula_version: string
  status: string
  message?: string | null
}

interface KPIResult {
  id: number
  report: number
  employee: Employee
  department?: Department | null
  role_snapshot: string
  score: string | number
  metrics_json: Record<string, any>
  breakdown_json: {
    timeliness?: number
    completion?: number
    workload?: number
    reliability?: number
    management?: number
    flags?: Record<string, any>
    [key: string]: any
  }
  flags_json: Record<string, any>
  created_at: string
}

interface KPIResponse {
  report: KPIReport
  results: KPIResult[]
}

export default function KPI() {
  const { user } = useAuthStore()
  const queryClient = useQueryClient()

  const userRole = user?.employee?.role
  const userDepartmentId = user?.employee?.department?.id
  const userEmployeeId = user?.employee?.id

  const isDirectorOrDeputy = userRole === 'director' || userRole === 'deputy'
  const isHead = userRole === 'head'
  const isRegular = !isDirectorOrDeputy && !isHead

  // Параметры фильтров
  const [year, setYear] = useState<number>(new Date().getFullYear())
  const [month, setMonth] = useState<number>(new Date().getMonth() + 1)
  const [selectedDepartmentId, setSelectedDepartmentId] = useState<string>('')
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>('')

  // Загрузка отделов
  const { data: departments } = useQuery<Department[]>({
    queryKey: ['departments'],
    queryFn: async () => {
      const response = await api.get('/departments/')
      return Array.isArray(response.data) ? response.data : response.data.results || []
    },
  })

  // Загрузка сотрудников (в целом, с последующей фильтрацией по отделу)
  const { data: employees } = useQuery<Employee[]>({
    queryKey: ['employees'],
    queryFn: async () => {
      const response = await api.get('/employees/')
      return Array.isArray(response.data) ? response.data : response.data.results || []
    },
  })

  // Применение дефолтов по отделу/сотруднику
  useEffect(() => {
    if (!selectedDepartmentId && userDepartmentId) {
      setSelectedDepartmentId(userDepartmentId.toString())
    }
    if (!selectedEmployeeId && userEmployeeId && isRegular) {
      setSelectedEmployeeId(userEmployeeId.toString())
    }
  }, [selectedDepartmentId, selectedEmployeeId, userDepartmentId, userEmployeeId, isRegular])

  const availableEmployees =
    employees?.filter((emp) => {
      if (selectedDepartmentId) {
        return emp.department?.id === parseInt(selectedDepartmentId)
      }
      return true
    }) || []

  // Загрузка KPI
  const {
    data: kpiData,
    isLoading,
    refetch,
  } = useQuery<KPIResponse>({
    queryKey: ['kpi', year, month, selectedDepartmentId, selectedEmployeeId],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.set('year', year.toString())
      params.set('month', month.toString())
      if (selectedDepartmentId) params.set('department_id', selectedDepartmentId)
      if (selectedEmployeeId) params.set('employee_id', selectedEmployeeId)
      const response = await api.get(`/kpi/results/?${params.toString()}`)
      return response.data
    },
  })

  // Генерация KPI (доступно только superuser — проверяется на backend)
  const generateMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/kpi/reports/generate/', {
        year,
        month,
      })
      return response.data as KPIReport
    },
    onSuccess: () => {
      toast.success('KPI за выбранный месяц успешно сформирован')
      queryClient.invalidateQueries({ queryKey: ['kpi'] })
      refetch()
    },
    onError: (error: any) => {
      const msg = error?.response?.data?.error || 'Ошибка при формировании KPI'
      toast.error(msg)
    },
  })

  const handleApplyFilters = () => {
    refetch()
  }

  const handleMonthInputChange = (value: string) => {
    if (!value) return
    const [y, m] = value.split('-')
    const parsedYear = parseInt(y, 10)
    const parsedMonth = parseInt(m, 10)
    if (!isNaN(parsedYear)) setYear(parsedYear)
    if (!isNaN(parsedMonth) && parsedMonth >= 1 && parsedMonth <= 12) setMonth(parsedMonth)
  }

  const monthValue = `${year}-${String(month).padStart(2, '0')}`

  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Award className="w-8 h-8" />
            KPI сотрудников
          </h1>
          <p className="text-muted-foreground mt-2">
            Ежемесячная оценка эффективности по задачам и срокам
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Label className="text-sm text-muted-foreground">Месяц</Label>
          <Input type="month" value={monthValue} onChange={(e) => handleMonthInputChange(e.target.value)} />
        </div>
      </div>

      {/* Фильтры и управление */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Фильтры
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Отдел и сотрудник */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Отдел</Label>
                <Select
                  value={selectedDepartmentId}
                  onChange={(e) => setSelectedDepartmentId(e.target.value)}
                  disabled={isHead || isRegular}
                >
                  {isDirectorOrDeputy && <option value="">Все отделы</option>}
                  {departments?.map((dept) => (
                    <option key={dept.id} value={dept.id.toString()}>
                      {dept.name}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Сотрудник</Label>
                <SearchableSelect
                  options={[
                    { value: '', label: 'Все сотрудники' },
                    ...availableEmployees.map((emp) => ({
                      value: emp.id.toString(),
                      label:
                        emp.full_name ||
                        `${emp.user.first_name} ${emp.user.last_name}` ||
                        emp.user.username,
                    })),
                  ]}
                  value={selectedEmployeeId}
                  onChange={(value) => setSelectedEmployeeId(value)}
                  placeholder={isRegular ? 'Только вы' : 'Все сотрудники'}
                  disabled={isRegular}
                  emptyText="Нет сотрудников"
                />
              </div>
            </div>

            {/* Кнопки */}
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground flex items-center gap-2">
                <Shield className="w-4 h-4" />
                <span>
                  Права доступа: директор и замы видят всех, руководитель – свой отдел, остальные – только себя.
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleApplyFilters}
                  disabled={isLoading}
                >
                  <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                  Обновить
                </Button>
                <Button
                  type="button"
                  onClick={() => generateMutation.mutate()}
                  disabled={generateMutation.isPending}
                >
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Сформировать KPI
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Таблица результатов */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Результаты KPI
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary" />
            </div>
          ) : !kpiData || kpiData.results.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">
              Нет данных KPI за выбранный период
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 pr-4">Сотрудник</th>
                    <th className="text-left py-2 pr-4">Отдел</th>
                    <th className="text-left py-2 pr-4">Роль</th>
                    <th className="text-right py-2 pr-4">Баллы</th>
                    <th className="text-right py-2 pr-4">Сроки</th>
                    <th className="text-right py-2 pr-4">Завершённость</th>
                    <th className="text-right py-2 pr-4">Нагрузка</th>
                    <th className="text-right py-2 pr-4">Управление</th>
                    <th className="text-left py-2">Комментарии</th>
                  </tr>
                </thead>
                <tbody>
                  {kpiData.results.map((row) => {
                    const breakdown = row.breakdown_json || {}
                    const flags = breakdown.flags || row.flags_json || {}

                    const fullName =
                      row.employee.full_name ||
                      `${row.employee.user.first_name} ${row.employee.user.last_name}` ||
                      row.employee.user.username

                    const deptName =
                      row.department?.name || row.employee.department?.name || '—'

                    const comments: string[] = []
                    if (flags.low_sample) comments.push('Мало задач за период')

                    return (
                      <tr key={row.id} className="border-b last:border-0">
                        <td className="py-2 pr-4">{fullName}</td>
                        <td className="py-2 pr-4">{deptName}</td>
                        <td className="py-2 pr-4">{row.role_snapshot}</td>
                        <td className="py-2 pr-4 text-right font-semibold">
                          {Number(row.score).toFixed(2)}
                        </td>
                        <td className="py-2 pr-4 text-right">
                          {breakdown.timeliness !== undefined
                            ? breakdown.timeliness.toFixed(1)
                            : '—'}
                        </td>
                        <td className="py-2 pr-4 text-right">
                          {breakdown.completion !== undefined
                            ? breakdown.completion.toFixed(1)
                            : '—'}
                        </td>
                        <td className="py-2 pr-4 text-right">
                          {breakdown.workload !== undefined
                            ? breakdown.workload.toFixed(1)
                            : '—'}
                        </td>
                        <td className="py-2 pr-4 text-right">
                          {breakdown.management !== undefined
                            ? breakdown.management.toFixed(1)
                            : '—'}
                        </td>
                        <td className="py-2 text-left text-xs text-muted-foreground">
                          {comments.join(' · ')}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

