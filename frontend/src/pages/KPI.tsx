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
import { BarChart3, Filter, RefreshCw, Award, Shield, Send } from 'lucide-react'
import { toast } from 'sonner'

interface Department {
  id: number
  name: string
  shortname?: string
  priority?: number
}

interface KPIReport {
  id: number
  year: number
  month: number
  generated_at: string
  status: 'draft' | 'published' | 'failed'
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

interface KPIRoleWeightsItem {
  id: number | null
  role: string
  role_display: string
  positive_weights: {
    timeliness?: number
    completion?: number
    workload?: number
    reliability?: number
    management?: number
  }
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
  const isSuperuser = user?.is_superuser === true

  const [year, setYear] = useState<number>(new Date().getFullYear())
  const [month, setMonth] = useState<number>(new Date().getMonth() + 1)
  const [selectedDepartmentId, setSelectedDepartmentId] = useState<string>('')
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>('')
  const [preview, setPreview] = useState<KPIResponse | null>(null)

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

  useEffect(() => {
    setPreview(null)
  }, [year, month])

  const availableEmployees =
    employees?.filter((emp) => {
      if (selectedDepartmentId) {
        return emp.department?.id === parseInt(selectedDepartmentId)
      }
      return true
    }) || []

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

  const displayData = preview ?? kpiData
  type SortKey =
    | 'employee'
    | 'department'
    | 'role'
    | 'score'
    | 'timeliness'
    | 'completion'
    | 'workload'
    | 'reliability'
    | 'management'

  const [sortKey, setSortKey] = useState<SortKey>('score')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const getEmployeeName = (row: KPIResult) =>
    row.employee.full_name ||
    `${row.employee.user.first_name} ${row.employee.user.last_name}` ||
    row.employee.user.username

  const getDepartmentName = (row: KPIResult) => {
    const deptAny = row.department as any
    const empDeptAny = row.employee.department as any
    return (
      deptAny?.shortname ||
      row.department?.name ||
      empDeptAny?.shortname ||
      row.employee.department?.name ||
      '—'
    )
  }

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'employee' || key === 'department' || key === 'role' ? 'asc' : 'desc')
    }
  }

  const getSortValue = (row: KPIResult, key: SortKey): string | number => {
    const b = row.breakdown_json || {}
    switch (key) {
      case 'employee':
        return getEmployeeName(row).toLowerCase()
      case 'department':
        return getDepartmentName(row).toLowerCase()
      case 'role':
        return row.role_snapshot.toLowerCase()
      case 'score':
        return Number(row.score) || 0
      case 'timeliness':
        return b.timeliness ?? 0
      case 'completion':
        return b.completion ?? 0
      case 'workload':
        return b.workload ?? 0
      case 'reliability':
        return b.reliability ?? 0
      case 'management':
        return b.management ?? 0
      default:
        return 0
    }
  }

  const generateMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/kpi/reports/generate/', { year, month })
      return response.data as KPIResponse
    },
    onSuccess: (data) => {
      toast.success('Предварительная оценка сформирована. Проверьте и нажмите «Опубликовать».')
      setPreview(data)
      queryClient.invalidateQueries({ queryKey: ['kpi'] })
      refetch()
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.error || 'Ошибка при формировании KPI')
    },
  })

  const publishMutation = useMutation({
    mutationFn: async (reportId: number) => {
      const response = await api.post(`/kpi/reports/${reportId}/publish/`)
      return response.data as KPIReport
    },
    onSuccess: () => {
      toast.success('KPI опубликован')
      setPreview(null)
      queryClient.invalidateQueries({ queryKey: ['kpi'] })
      refetch()
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.error || 'Ошибка публикации')
    },
  })

  // Настройки весов KPI по ролям (только для суперпользователя)
  const { data: weightsList } = useQuery<KPIRoleWeightsItem[]>({
    queryKey: ['kpi-weights'],
    queryFn: async () => {
      const response = await api.get('/kpi/weights/')
      return response.data
    },
    enabled: isSuperuser,
  })

  const [weightsEdits, setWeightsEdits] = useState<
    Record<string, Partial<KPIRoleWeightsItem['positive_weights']>>
  >({})

  const getWeightsForRole = (role: string): KPIRoleWeightsItem['positive_weights'] => {
    const base =
      weightsList?.find((w) => w.role === role)?.positive_weights || {
        timeliness: 30,
        completion: 25,
        workload: 20,
        reliability: 15,
        management: 10,
      }
    const edit = weightsEdits[role]
    return edit ? { ...base, ...edit } : base
  }

  const updateWeightsEdit = (
    role: string,
    field: keyof KPIRoleWeightsItem['positive_weights'],
    value: number
  ) => {
    setWeightsEdits((prev) => ({
      ...prev,
      [role]: {
        ...(prev[role] || {}),
        [field]: value,
      },
    }))
  }

  const saveWeightsMutation = useMutation({
    mutationFn: async ({ role, weights }: { role: string; weights: KPIRoleWeightsItem['positive_weights'] }) => {
      const response = await api.put(`/kpi/weights/${role}/`, {
        positive_weights: weights,
      })
      return response.data as KPIRoleWeightsItem
    },
    onSuccess: () => {
      toast.success('Веса KPI для роли сохранены')
      queryClient.invalidateQueries({ queryKey: ['kpi-weights'] })
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.error || 'Ошибка сохранения весов')
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
                  {(isDirectorOrDeputy || isSuperuser) && <option value="">Все отделы</option>}
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
                  Админ и директор видят все оценки; руководитель — свой отдел; остальные — только себя.
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
                {isSuperuser && (
                  <Button
                    type="button"
                    onClick={() => generateMutation.mutate()}
                    disabled={generateMutation.isPending}
                  >
                    <BarChart3 className="w-4 h-4 mr-2" />
                    Сформировать KPI
                  </Button>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Настройки весов KPI по ролям (только для администратора) */}
      {isSuperuser && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Настройки весов KPI по ролям
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Задайте, какой вклад (в баллах) дают блоки «Сроки», «Завершённость», «Нагрузка», «Надёжность» и «Управление» для каждой роли.
            </p>
          </CardHeader>
          <CardContent>
            {!weightsList ? (
              <div className="flex justify-center py-4">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
              </div>
            ) : (
              <div className="space-y-4">
                {weightsList.map((item) => {
                  const w = getWeightsForRole(item.role)
                  const sum =
                    (w.timeliness || 0) +
                    (w.completion || 0) +
                    (w.workload || 0) +
                    (w.reliability || 0) +
                    (w.management || 0)

                  return (
                    <div key={item.role} className="border rounded-lg p-4 space-y-3">
                      <div className="flex items-center justify-between gap-4">
                        <div className="font-medium">{item.role_display}</div>
                        <div className="text-xs text-muted-foreground">
                          Сумма весов:{' '}
                          <span className={Math.round(sum) !== 100 ? 'text-amber-600 font-semibold' : ''}>
                            {sum.toFixed(1)}
                          </span>{' '}
                          (рекомендуется около 100)
                        </div>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
                        <div className="space-y-1">
                          <Label className="text-xs">Сроки</Label>
                          <Input
                            type="number"
                            step="1"
                            value={w.timeliness ?? 0}
                            onChange={(e) =>
                              updateWeightsEdit(item.role, 'timeliness', Number(e.target.value) || 0)
                            }
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Завершённость</Label>
                          <Input
                            type="number"
                            step="1"
                            value={w.completion ?? 0}
                            onChange={(e) =>
                              updateWeightsEdit(item.role, 'completion', Number(e.target.value) || 0)
                            }
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Нагрузка</Label>
                          <Input
                            type="number"
                            step="1"
                            value={w.workload ?? 0}
                            onChange={(e) =>
                              updateWeightsEdit(item.role, 'workload', Number(e.target.value) || 0)
                            }
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Надёжность</Label>
                          <Input
                            type="number"
                            step="1"
                            value={w.reliability ?? 0}
                            onChange={(e) =>
                              updateWeightsEdit(item.role, 'reliability', Number(e.target.value) || 0)
                            }
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Управление</Label>
                          <Input
                            type="number"
                            step="1"
                            value={w.management ?? 0}
                            onChange={(e) =>
                              updateWeightsEdit(item.role, 'management', Number(e.target.value) || 0)
                            }
                          />
                        </div>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => saveWeightsMutation.mutate({ role: item.role, weights: w })}
                        disabled={saveWeightsMutation.isPending}
                      >
                        Сохранить веса для роли
                      </Button>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Таблица результатов */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Результаты KPI
              {displayData?.report?.status === 'draft' && (
                <span className="text-sm font-normal text-amber-600 bg-amber-50 dark:bg-amber-950/30 px-2 py-0.5 rounded">
                  Черновик
                </span>
              )}
            </CardTitle>
            {isSuperuser && displayData?.report?.status === 'draft' && (
              <Button
                onClick={() => publishMutation.mutate(displayData.report.id)}
                disabled={publishMutation.isPending}
              >
                <Send className="w-4 h-4 mr-2" />
                Опубликовать
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary" />
            </div>
          ) : !displayData || displayData.results.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">
              Нет данных KPI за выбранный период
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 pr-4">
                      <button
                        type="button"
                        className="font-semibold"
                        onClick={() => handleSort('employee')}
                      >
                        Сотрудник
                      </button>
                    </th>
                    <th className="text-left py-2 pr-4">
                      <button
                        type="button"
                        className="font-semibold"
                        onClick={() => handleSort('department')}
                      >
                        Отдел
                      </button>
                    </th>
                    <th className="text-left py-2 pr-4">
                      <button
                        type="button"
                        className="font-semibold"
                        onClick={() => handleSort('role')}
                      >
                        Роль
                      </button>
                    </th>
                    <th className="text-right py-2 pr-4">
                      <button
                        type="button"
                        className="font-semibold"
                        onClick={() => handleSort('score')}
                      >
                        Баллы
                      </button>
                    </th>
                    <th className="text-right py-2 pr-4">
                      <button
                        type="button"
                        className="font-semibold"
                        onClick={() => handleSort('timeliness')}
                      >
                        Сроки
                      </button>
                    </th>
                    <th className="text-right py-2 pr-4">
                      <button
                        type="button"
                        className="font-semibold"
                        onClick={() => handleSort('completion')}
                      >
                        Завершённость
                      </button>
                    </th>
                    <th className="text-right py-2 pr-4">
                      <button
                        type="button"
                        className="font-semibold"
                        onClick={() => handleSort('workload')}
                      >
                        Нагрузка
                      </button>
                    </th>
                    <th className="text-right py-2 pr-4">
                      <button
                        type="button"
                        className="font-semibold"
                        onClick={() => handleSort('reliability')}
                      >
                        Надёжность
                      </button>
                    </th>
                    <th className="text-right py-2 pr-4">
                      <button
                        type="button"
                        className="font-semibold"
                        onClick={() => handleSort('management')}
                      >
                        Управление
                      </button>
                    </th>
                    <th className="text-left py-2">Комментарии</th>
                  </tr>
                </thead>
                <tbody>
                  {[...displayData.results]
                    .sort((a, b) => {
                      const av = getSortValue(a, sortKey)
                      const bv = getSortValue(b, sortKey)
                      if (typeof av === 'string' && typeof bv === 'string') {
                        const res = av.localeCompare(bv)
                        return sortDir === 'asc' ? res : -res
                      }
                      const na = Number(av) || 0
                      const nb = Number(bv) || 0
                      if (na === nb) return 0
                      const res = na < nb ? -1 : 1
                      return sortDir === 'asc' ? res : -res
                    })
                    .map((row) => {
                    const breakdown = row.breakdown_json || {}
                    const flags = breakdown.flags || row.flags_json || {}

                    const fullName = getEmployeeName(row)
                    const deptName = getDepartmentName(row)

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
                          {breakdown.reliability !== undefined
                            ? breakdown.reliability.toFixed(1)
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

