import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Employee } from '@/types/task'
import { User, Building2, Briefcase, Crown, Phone } from 'lucide-react'
import { useMemo } from 'react'

export default function Employees() {
  const { data: employees, isLoading } = useQuery<Employee[]>({
    queryKey: ['employees'],
    queryFn: async () => {
      const response = await api.get('/employees/')
      return Array.isArray(response.data) ? response.data : (response.data.results || [])
    },
  })

  // Группируем сотрудников по отделам
  const groupedEmployees = useMemo(() => {
    if (!employees) return []
    
    const grouped: Record<number, { department: { id: number; name: string; priority?: number }; employees: Employee[] }> = {}
    
    employees.forEach((employee) => {
      const deptId = employee.department?.id || 0
      const deptName = employee.department?.name || 'Без отдела'
      const deptPriority = employee.department?.priority ?? 999 // Без отдела в конец
      
      if (!grouped[deptId]) {
        grouped[deptId] = {
          department: { id: deptId, name: deptName, priority: deptPriority },
          employees: []
        }
      }
      
      grouped[deptId].employees.push(employee)
    })
    
    // Сортируем сотрудников в каждом отделе: сначала руководитель, потом остальные
    Object.values(grouped).forEach((group) => {
      group.employees.sort((a, b) => {
        // Руководитель отдела всегда первый
        if (a.role === 'head' && b.role !== 'head') return -1
        if (a.role !== 'head' && b.role === 'head') return 1
        // Остальные сортируем по имени
        const nameA = a.full_name || a.user.username
        const nameB = b.full_name || b.user.username
        return nameA.localeCompare(nameB, 'ru')
      })
    })
    
    // Сортируем отделы по приоритету (меньше = выше), затем по имени
    const sortedGroups = Object.values(grouped).sort((a, b) => {
      const priorityA = a.department.priority ?? 999
      const priorityB = b.department.priority ?? 999
      if (priorityA !== priorityB) {
        return priorityA - priorityB
      }
      return a.department.name.localeCompare(b.department.name, 'ru')
    })
    
    // Возвращаем массив вместо объекта для сохранения порядка
    return sortedGroups
  }, [employees])

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
        <h1 className="text-3xl font-bold">Сотрудники</h1>
        <p className="text-muted-foreground mt-2">
          Список всех сотрудников организации
        </p>
      </div>

      {employees && employees.length > 0 ? (
        <div className="space-y-6">
          {groupedEmployees.map((group) => (
            <div key={group.department.id} className="space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b">
                <Building2 className="w-5 h-5 text-primary" />
                <h2 className="text-xl font-semibold">{group.department.name}</h2>
              </div>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {group.employees.map((employee) => {
                  return (
                    <Card 
                      key={employee.id} 
                      className="hover:shadow-lg transition-shadow"
                    >
                      <CardHeader>
                        <div className="flex items-center gap-3">
                          <div className="w-12 h-12 rounded-full border-2 border-muted overflow-hidden flex-shrink-0">
                            {employee.photo_url ? (
                              <img
                                src={employee.photo_url}
                                alt={employee.full_name}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                  const target = e.target as HTMLImageElement
                                  target.style.display = 'none'
                                  const fallback = target.nextElementSibling as HTMLElement
                                  if (fallback) {
                                    fallback.style.display = 'flex'
                                  }
                                }}
                              />
                            ) : null}
                            <div 
                              className={`w-full h-full flex items-center justify-center text-white font-semibold bg-muted ${employee.photo_url ? 'hidden' : 'flex'}`}
                            >
                              {employee.middlename?.[0] || employee.user.username[0].toUpperCase()}
                              {employee.firstname?.[0] || ''}
                            </div>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <CardTitle className="text-lg truncate">
                                {employee.full_name_complete || employee.full_name}
                              </CardTitle>
                              {(employee.role === 'director' || employee.role === 'deputy') && (
                                <Crown className="w-4 h-4 text-primary flex-shrink-0" />
                              )}
                            </div>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {employee.position && (
                          <div className="flex items-center gap-2 text-sm">
                            <Briefcase className="w-4 h-4 text-muted-foreground" />
                            <span>{employee.position}</span>
                          </div>
                        )}
                        {employee.internal_phone && (
                          <div className="flex items-center gap-2 text-sm">
                            <Phone className="w-4 h-4 text-muted-foreground" />
                            <span>{employee.internal_phone}</span>
                          </div>
                        )}
                        <Button asChild variant="outline" className="w-full mt-4">
                          <Link to={`/employees/${employee.id}`}>
                            <User className="w-4 h-4 mr-2" />
                            Подробнее
                          </Link>
                        </Button>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Нет сотрудников</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
