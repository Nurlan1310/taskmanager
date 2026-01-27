import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { toast } from 'sonner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select } from '@/components/ui/select'
import { ArrowLeft, Save } from 'lucide-react'
import { Link } from 'react-router-dom'
import EmployeeModal from '@/components/EmployeeModal'
import DepartmentSelector from '@/components/DepartmentSelector'

interface CardFormData {
  title: string
  description: string
  start_date: string
  end_date: string
  responsible_department_id: number | null
  has_plan: boolean
  categories_ids: number[]
  plan_file?: File | null
  approvers_ids: number[]
  final_approver: number | null
  shared_departments_ids: number[]
}

export default function CreateCard() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<CardFormData>({
    title: '',
    description: '',
    start_date: '',
    end_date: '',
    responsible_department_id: null,
    has_plan: false,
    categories_ids: [],
    plan_file: null,
    approvers_ids: [],
    final_approver: null,
    shared_departments_ids: [],
  })

  const hasPlan = formData.has_plan
  const [selectedCategories, setSelectedCategories] = useState<number[]>([])
  const [selectedApprovers, setSelectedApprovers] = useState<number[]>([])
  const [selectedSharedDepartments, setSelectedSharedDepartments] = useState<number[]>([])
  const [showApproversModal, setShowApproversModal] = useState(false)
  const [showSharedDeptsModal, setShowSharedDeptsModal] = useState(false)
  const [showFinalApproverModal, setShowFinalApproverModal] = useState(false)
  
  // Получаем данные текущего пользователя с полной информацией
  const { data: currentUser } = useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const response = await api.get('/auth/me/')
      return response.data
    },
  })

  // Проверяем, может ли пользователь менять отдел
  const canChangeDepartment = currentUser?.employee?.role === 'director' || currentUser?.employee?.role === 'deputy'

  const { data: departments } = useQuery({
    queryKey: ['departments'],
    queryFn: async () => {
      const response = await api.get('/departments/')
      const depts = Array.isArray(response.data) ? response.data : (response.data.results || [])
      // Сортируем отделы по приоритету (меньше = выше), затем по имени
      return depts.sort((a: any, b: any) => {
        const priorityA = a.priority ?? 999
        const priorityB = b.priority ?? 999
        if (priorityA !== priorityB) {
          return priorityA - priorityB
        }
        return a.name.localeCompare(b.name, 'ru')
      })
    },
  })

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const response = await api.get('/categories/')
      return Array.isArray(response.data) ? response.data : (response.data.results || [])
    },
  })

  const { data: employees } = useQuery({
    queryKey: ['employees'],
    queryFn: async () => {
      const response = await api.get('/employees/')
      return Array.isArray(response.data) ? response.data : (response.data.results || [])
    },
  })

  // Устанавливаем отдел пользователя по умолчанию
  useEffect(() => {
    if (currentUser?.employee?.department?.id && !formData.responsible_department_id) {
      setFormData(prev => ({
        ...prev,
        responsible_department_id: currentUser.employee!.department!.id
      }))
    }
  }, [currentUser, formData.responsible_department_id])

  const createCardMutation = useMutation({
    mutationFn: async (data: CardFormData) => {
      const formDataToSend = new FormData()
      formDataToSend.append('title', data.title)
      formDataToSend.append('description', data.description || '')
      formDataToSend.append('start_date', data.start_date)
      formDataToSend.append('end_date', data.end_date)
      if (data.responsible_department_id) {
        formDataToSend.append('responsible_department_id', data.responsible_department_id.toString())
      }
      formDataToSend.append('has_plan', data.has_plan.toString())
      
      selectedCategories.forEach(id => formDataToSend.append('categories_ids', id.toString()))
      selectedApprovers.forEach(id => formDataToSend.append('approvers_ids', id.toString()))
      selectedSharedDepartments.forEach(id => formDataToSend.append('shared_departments_ids', id.toString()))
      
      if (data.final_approver) {
        formDataToSend.append('final_approver_id', data.final_approver.toString())
      }
      
      if (data.plan_file) {
        formDataToSend.append('plan_file', data.plan_file)
      }
      
      return api.post('/cards/', formDataToSend, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
    },
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['cards'] })
      toast.success('Карточка мероприятия создана')
      navigate(`/cards/${response.data.id}`)
    },
    onError: (error: any) => {
      console.error('Ошибка при создании карточки:', error)
      alert(error?.response?.data?.error || 'Ошибка при создании мероприятия')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Валидация
    if (!formData.title.trim()) {
      alert('Введите название мероприятия')
      return
    }
    if (!formData.start_date) {
      alert('Выберите дату начала')
      return
    }
    if (!formData.end_date) {
      alert('Выберите дату окончания')
      return
    }
    if (new Date(formData.end_date) < new Date(formData.start_date)) {
      alert('Дата окончания не может быть раньше даты начала')
      return
    }
    if (formData.has_plan) {
      if (!formData.plan_file) {
        alert('Загрузите файл плана мероприятия')
        return
      }
      if (!formData.final_approver) {
        alert('Выберите финального утверждающего')
        return
      }
    }
    
    createCardMutation.mutate(formData)
  }

  const handleChange = (field: keyof CardFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const toggleCategory = (categoryId: number) => {
    setSelectedCategories(prev =>
      prev.includes(categoryId)
        ? prev.filter(id => id !== categoryId)
        : [...prev, categoryId]
    )
  }

  const toggleApprover = (employeeId: number) => {
    setSelectedApprovers(prev =>
      prev.includes(employeeId)
        ? prev.filter(id => id !== employeeId)
        : [...prev, employeeId]
    )
  }

  const toggleSharedDepartment = (deptId: number) => {
    setSelectedSharedDepartments(prev =>
      prev.includes(deptId)
        ? prev.filter(id => id !== deptId)
        : [...prev, deptId]
    )
  }

  // Фильтруем сотрудников для согласующих (исключаем staff)
  const approverCandidates = employees?.filter((emp: any) => emp.role !== 'staff') || []
  
  // Фильтруем сотрудников для финального утверждающего (только director и deputy)
  const finalApproverCandidates = employees?.filter((emp: any) => 
    emp.role === 'director' || emp.role === 'deputy'
  ) || []

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/cards">
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </Button>
        <h1 className="text-3xl font-bold">Создать мероприятие</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Основная информация</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="text-sm font-medium mb-2 block">
                Название мероприятия <span className="text-red-500">*</span>
              </label>
              <Input
                value={formData.title}
                onChange={(e) => handleChange('title', e.target.value)}
                placeholder="Введите название мероприятия"
                required
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Описание</label>
              <Textarea
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder="Описание мероприятия"
                rows={4}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Дата начала <span className="text-red-500">*</span>
                </label>
                <Input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => handleChange('start_date', e.target.value)}
                  required
                />
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">
                  Дата окончания <span className="text-red-500">*</span>
                </label>
                <Input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => handleChange('end_date', e.target.value)}
                  required
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">
                Ответственный отдел
                {!canChangeDepartment && <span className="text-xs text-muted-foreground ml-2">(ваш отдел)</span>}
              </label>
              <Select
                value={formData.responsible_department_id || ''}
                onChange={(e) => handleChange('responsible_department_id', e.target.value ? parseInt(e.target.value) : null)}
                disabled={!canChangeDepartment}
              >
                {departments?.map((dept: any) => (
                  <option key={dept.id} value={dept.id}>
                    {dept.name}
                  </option>
                ))}
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Категории (необязательно)</label>
              <div className="flex flex-wrap gap-2 mb-2 min-h-[40px] p-2 border rounded-md">
                {selectedCategories.length === 0 ? (
                  <span className="text-sm text-muted-foreground">Не выбрано</span>
                ) : (
                  selectedCategories.map((id) => {
                    const cat = categories?.find((c: any) => c.id === id)
                    return cat ? (
                      <div
                        key={id}
                        className="px-3 py-1 bg-primary text-primary-foreground rounded-full text-sm flex items-center gap-2"
                      >
                        {cat.name}
                        <button
                          type="button"
                          onClick={() => toggleCategory(id)}
                          className="ml-1 hover:bg-primary-foreground/20 rounded-full w-4 h-4 flex items-center justify-center"
                        >
                          ×
                        </button>
                      </div>
                    ) : null
                  })
                )}
              </div>
              {categories && categories.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {categories.map((cat: any) => (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => toggleCategory(cat.id)}
                      className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                        selectedCategories.includes(cat.id)
                          ? 'bg-primary text-primary-foreground border-primary'
                          : 'bg-background hover:bg-accent'
                      }`}
                    >
                      {cat.name}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Смежные отделы (необязательно)</label>
              <div className="flex flex-wrap gap-2 mb-2 min-h-[40px] p-2 border rounded-md">
                {selectedSharedDepartments.length === 0 ? (
                  <span className="text-sm text-muted-foreground">Не выбрано</span>
                ) : (
                  selectedSharedDepartments.map((id) => {
                    const dept = departments?.find((d: any) => d.id === id)
                    return dept ? (
                      <div
                        key={id}
                        className="px-3 py-1 bg-primary text-primary-foreground rounded-full text-sm flex items-center gap-2"
                      >
                        {dept.name}
                        <button
                          type="button"
                          onClick={() => toggleSharedDepartment(id)}
                          className="ml-1 hover:bg-primary-foreground/20 rounded-full w-4 h-4 flex items-center justify-center"
                        >
                          ×
                        </button>
                      </div>
                    ) : null
                  })
                )}
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowSharedDeptsModal(true)}
              >
                Выбрать отделы
              </Button>
            </div>

            <div className="border-t pt-6">
              <div className="flex items-center gap-2 mb-4">
                <input
                  type="checkbox"
                  id="has_plan"
                  checked={formData.has_plan}
                  onChange={(e) => handleChange('has_plan', e.target.checked)}
                  className="w-4 h-4"
                />
                <label htmlFor="has_plan" className="text-sm font-medium cursor-pointer">
                  Мероприятие с планом (требует согласования)
                </label>
              </div>

            {hasPlan && (
              <div className="p-4 bg-accent rounded-lg space-y-4 border border-primary/20">
                <p className="text-sm font-medium mb-4">
                  Для мероприятия с планом необходимо:
                </p>

                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Файл плана мероприятия {formData.has_plan && <span className="text-red-500">*</span>}
                  </label>
                  <Input
                    type="file"
                    accept=".pdf,.doc,.docx,.xls,.xlsx"
                    onChange={(e) => {
                      const file = e.target.files?.[0] || null
                      handleChange('plan_file', file)
                    }}
                    required={formData.has_plan}
                  />
                </div>

                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Согласующие
                  </label>
                  <div className="flex flex-wrap gap-2 mb-2 min-h-[40px] p-2 border rounded-md">
                    {selectedApprovers.map((id) => {
                      const emp = approverCandidates.find((e: any) => e.id === id)
                      return emp ? (
                        <div
                          key={id}
                          className="px-3 py-1 bg-primary text-primary-foreground rounded-full text-sm flex items-center gap-2"
                        >
                          {emp.full_name_complete || emp.full_name} {emp.position && `(${emp.position})`}
                          <button
                            type="button"
                            onClick={() => toggleApprover(id)}
                            className="ml-1 hover:bg-primary-foreground/20 rounded-full w-4 h-4 flex items-center justify-center"
                          >
                            ×
                          </button>
                        </div>
                      ) : null
                    })}
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setShowApproversModal(true)}
                  >
                    Выбрать согласующих
                  </Button>
                </div>

                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Финальный утверждающий {formData.has_plan && <span className="text-red-500">*</span>}
                  </label>
                  <div className="flex items-center gap-2 mb-2">
                    {formData.final_approver ? (
                      <div className="px-3 py-1 bg-primary text-primary-foreground rounded-full text-sm flex items-center gap-2">
                        {finalApproverCandidates.find((e: any) => e.id === formData.final_approver)?.full_name_complete || finalApproverCandidates.find((e: any) => e.id === formData.final_approver)?.full_name}
                        <button
                          type="button"
                          onClick={() => handleChange('final_approver', null)}
                          className="ml-1 hover:bg-primary-foreground/20 rounded-full w-4 h-4 flex items-center justify-center"
                        >
                          ×
                        </button>
                      </div>
                    ) : (
                      <span className="text-sm text-muted-foreground">Не выбран</span>
                    )}
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setShowFinalApproverModal(true)}
                  >
                    Выбрать утверждающего
                  </Button>
                </div>
              </div>
            )}
            </div>

            <div className="flex gap-4">
              <Button type="submit" disabled={createCardMutation.isPending}>
                <Save className="w-4 h-4 mr-2" />
                {createCardMutation.isPending ? 'Создание...' : 'Создать мероприятие'}
              </Button>
              <Button type="button" variant="outline" asChild>
                <Link to="/cards">Отмена</Link>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Модальное окно выбора согласующих */}
      <EmployeeModal
        isOpen={showApproversModal}
        onClose={() => setShowApproversModal(false)}
        employees={employees || []}
        selectedIds={selectedApprovers}
        onToggle={toggleApprover}
        filter={(emp) => emp.role !== 'staff'}
        title="Выберите согласующих"
      />

      {/* Модальное окно выбора смежных отделов */}
      {showSharedDeptsModal && departments && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowSharedDeptsModal(false)}
        >
          <Card 
            className="w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <CardHeader>
              <CardTitle>Выберите смежные отделы</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto">
              <DepartmentSelector
                departments={departments}
                selectedIds={selectedSharedDepartments}
                onToggle={toggleSharedDepartment}
                title="Выберите смежные отделы"
              />
            </CardContent>
            <div className="p-4 border-t">
              <Button onClick={() => setShowSharedDeptsModal(false)} className="w-full">
                Готово
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Модальное окно выбора финального утверждающего */}
      <EmployeeModal
        isOpen={showFinalApproverModal}
        onClose={() => setShowFinalApproverModal(false)}
        employees={employees || []}
        selectedIds={formData.final_approver ? [formData.final_approver] : []}
        onToggle={(id) => {
          if (formData.final_approver === id) {
            handleChange('final_approver', null)
          } else {
            handleChange('final_approver', id)
          }
        }}
        filter={(emp) => emp.role === 'director' || emp.role === 'deputy'}
        title="Выберите финального утверждающего"
      />
    </div>
  )
}

