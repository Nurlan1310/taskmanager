interface Department {
  id: number
  name: string
  priority?: number
}

interface DepartmentSelectorProps {
  departments: Department[]
  selectedIds: number[]
  onToggle: (id: number) => void
  title?: string
}

export default function DepartmentSelector({
  departments,
  selectedIds,
  onToggle,
}: DepartmentSelectorProps) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {departments.map((dept) => (
          <button
            key={dept.id}
            type="button"
            onClick={() => onToggle(dept.id)}
            className={`px-3 py-1 rounded-full text-sm border transition-colors ${
              selectedIds.includes(dept.id)
                ? 'bg-primary text-primary-foreground border-primary'
                : 'bg-background hover:bg-accent'
            }`}
          >
            {dept.name}
          </button>
        ))}
      </div>
    </div>
  )
}

