import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Employee } from '@/types/task'

interface EmployeeSelectorProps {
  employees: Employee[]
  selectedIds: number[]
  onToggle: (id: number) => void
  filter?: (emp: Employee) => boolean
  title?: string
}

export default function EmployeeSelector({
  employees,
  selectedIds,
  onToggle,
  filter,
}: EmployeeSelectorProps) {
  const [expandedDepartments, setExpandedDepartments] = useState<Set<number>>(new Set())

  // Фильтруем сотрудников если нужно
  const filteredEmployees = filter ? employees.filter(filter) : employees

  // Группируем по отделам
  const employeesByDepartment = filteredEmployees.reduce((acc, emp) => {
    const deptId = emp.department?.id || 0
    const deptName = emp.department?.name || 'Без отдела'
    const deptPriority = emp.department?.priority ?? 999 // Без отдела в конец
    
    if (!acc[deptId]) {
      acc[deptId] = {
        id: deptId,
        name: deptName,
        priority: deptPriority,
        employees: [],
      }
    }
    acc[deptId].employees.push(emp)
    return acc
  }, {} as Record<number, { id: number; name: string; priority?: number; employees: Employee[] }>)

  // Сортируем отделы по приоритету (меньше = выше), затем по имени
  const departments = Object.values(employeesByDepartment).sort((a, b) => {
    const priorityA = a.priority ?? 999
    const priorityB = b.priority ?? 999
    if (priorityA !== priorityB) {
      return priorityA - priorityB
    }
    return a.name.localeCompare(b.name, 'ru')
  })

  const toggleDepartment = (deptId: number) => {
    setExpandedDepartments(prev => {
      const next = new Set(prev)
      if (next.has(deptId)) {
        next.delete(deptId)
      } else {
        next.add(deptId)
      }
      return next
    })
  }

  return (
    <div className="space-y-2">
      {departments.map((dept) => {
        const isExpanded = expandedDepartments.has(dept.id)
        const selectedInDept = dept.employees.filter(emp => selectedIds.includes(emp.id)).length
        
        return (
          <div key={dept.id} className="border rounded-lg">
            <button
              type="button"
              onClick={() => toggleDepartment(dept.id)}
              className="w-full flex items-center justify-between p-3 hover:bg-accent transition-colors"
            >
              <div className="flex items-center gap-2">
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                )}
                <span className="font-medium">{dept.name}</span>
                {selectedInDept > 0 && (
                  <span className="text-sm text-muted-foreground">
                    ({selectedInDept} выбрано)
                  </span>
                )}
              </div>
            </button>
            
            {isExpanded && (
              <div className="border-t bg-muted/30">
                {dept.employees.map((emp) => (
                  <label
                    key={emp.id}
                    className="flex items-center gap-3 p-3 hover:bg-accent/50 cursor-pointer border-b last:border-b-0"
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(emp.id)}
                      onChange={() => onToggle(emp.id)}
                      className="w-4 h-4"
                    />
                    <div className="flex-1">
                      <p className="font-medium">
                        {emp.full_name_complete || emp.full_name}
                      </p>
                      {emp.position && (
                        <p className="text-sm text-muted-foreground">{emp.position}</p>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

