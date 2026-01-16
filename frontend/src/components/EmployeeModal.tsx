import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { X } from 'lucide-react'
import EmployeeSelector from './EmployeeSelector'
import { Employee } from '@/types/task'

interface EmployeeModalProps {
  isOpen: boolean
  onClose: () => void
  employees: Employee[]
  selectedIds: number[]
  onToggle: (id: number) => void
  filter?: (emp: Employee) => boolean
  title?: string
}

export default function EmployeeModal({
  isOpen,
  onClose,
  employees,
  selectedIds,
  onToggle,
  filter,
  title = 'Выберите сотрудников',
}: EmployeeModalProps) {
  if (!isOpen) return null

  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <Card 
        className="w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle>{title}</CardTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
          >
            <X className="w-4 h-4" />
          </Button>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto">
          <EmployeeSelector
            employees={employees}
            selectedIds={selectedIds}
            onToggle={onToggle}
            filter={filter}
            title={title}
          />
        </CardContent>
        <div className="p-4 border-t">
          <Button onClick={onClose} className="w-full">
            Готово
          </Button>
        </div>
      </Card>
    </div>
  )
}

