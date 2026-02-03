import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Task, Employee } from '@/types/task'
import { useAuthStore } from '@/store/authStore'
import { 
  ArrowLeft, 
  Calendar, 
  User, 
  FileText, 
  Clock,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Paperclip,
  History,
  Share2,
  Edit,
  Trash2
} from 'lucide-react'
import { useState } from 'react'
import { formatDateTimeInAstanaTime } from '@/lib/dateUtils'
import { toast } from 'sonner'

const statusLabels: Record<string, string> = {
  new: 'Новая',
  in_progress: 'В работе',
  done: 'Выполнена',
  under_review: 'На проверке',
  sent_for_review: 'Отправлено на проверку',
  rejected: 'Отклонена',
  pending: 'На согласовании',
  revision: 'На пересмотрении',
  send_for_approve: 'Отправлено на согласование',
}

const statusColors: Record<string, string> = {
  new: 'bg-gray-500',
  in_progress: 'bg-yellow-500',
  done: 'bg-green-500',
  under_review: 'bg-blue-500',
  sent_for_review: 'bg-purple-500',
  rejected: 'bg-red-500',
  pending: 'bg-orange-500',
  revision: 'bg-amber-500',
  send_for_approve: 'bg-indigo-500',
}

const historyActionColors: Record<string, string> = {
  created: 'bg-blue-500',
  assigned: 'bg-purple-500',
  taken: 'bg-yellow-500',
  sent_for_review: 'bg-purple-500',
  under_review: 'bg-indigo-500',
  rejected: 'bg-red-500',
  redirected: 'bg-pink-500',
  executed: 'bg-green-500',
  done: 'bg-emerald-500',
  approved: 'bg-green-500',
}

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [showHistoryModal, setShowHistoryModal] = useState(false)
  const [showRedirectModal, setShowRedirectModal] = useState(false)
  const [selectedRedirectEmployeeId, setSelectedRedirectEmployeeId] = useState<number | null>(null)
  const { user } = useAuthStore()

  const { data: task, isLoading, error } = useQuery<Task>({
    queryKey: ['task', id],
    queryFn: async () => {
      try {
        const response = await api.get(`/tasks/${id}/`)
        return response.data
      } catch (err: any) {
        // Если ошибка доступа (403), пробрасываем её дальше
        if (err.response?.status === 403) {
          throw new Error('access_denied')
        }
        // Если ошибка 404 или другая, логируем и пробрасываем
        console.error('Error loading task:', err)
        throw err
      }
    },
    retry: false, // Не повторять запрос при ошибке
  })

  const takeTaskMutation = useMutation({
    mutationFn: async () => {
      return api.post(`/tasks/${id}/take/`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      toast.success('Задача принята в работу')
    },
  })

  // Получаем текущего пользователя для проверки роли
  const { data: currentUser } = useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const response = await api.get('/auth/me/')
      return response.data
    },
  })

  // Получаем список сотрудников для перенаправления
  const { data: employees } = useQuery<Employee[]>({
    queryKey: ['employees'],
    queryFn: async () => {
      const response = await api.get('/employees/')
      return Array.isArray(response.data) ? response.data : (response.data.results || [])
    },
  })

  // Фильтруем сотрудников в зависимости от роли
  const availableEmployeesForRedirect = employees?.filter((emp) => {
    const userRole = currentUser?.employee?.role
    const userDepartmentId = currentUser?.employee?.department?.id
    
    if (userRole === 'deputy') {
      // Заместитель может перенаправить любому сотруднику
      return emp.id !== currentUser?.employee?.id // Исключаем себя
    } else if (userRole === 'head') {
      // Руководитель может перенаправить только сотрудникам своего отдела
      return emp.department?.id === userDepartmentId && emp.id !== currentUser?.employee?.id
    }
    return false
  }) || []

  const redirectTaskMutation = useMutation({
    mutationFn: async (employeeId: number) => {
      return api.post(`/tasks/${id}/redirect/`, { employee_id: employeeId })
    },
    onSuccess: (_, employeeId) => {
      const employee = availableEmployeesForRedirect.find(emp => emp.id === employeeId)
      const employeeName = employee?.full_name || employee?.full_name_complete || 'сотруднику'
      queryClient.invalidateQueries({ queryKey: ['task', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      toast.success(`Задача перенаправлена ${employeeName}`)
      setShowRedirectModal(false)
      setSelectedRedirectEmployeeId(null)
    },
    onError: (error: any) => {
      alert(error?.response?.data?.error || 'Ошибка при перенаправлении задачи')
    },
  })

  const returnRedirectMutation = useMutation({
    mutationFn: async () => {
      return api.post(`/tasks/${id}/return-redirect/`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      queryClient.invalidateQueries({ queryKey: ['assignments'] })
      toast.success('Задача возвращена вам')
    },
    onError: (error: any) => {
      alert(error?.response?.data?.error || 'Ошибка при возврате задачи')
    },
  })

  const recallTaskMutation = useMutation({
    mutationFn: async () => {
      return api.post(`/tasks/${id}/recall/`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success('Задача успешно отозвана')
    },
    onError: (error: any) => {
      alert(error?.response?.data?.error || 'Ошибка при отзыве задачи')
    },
  })

  const handleRecall = () => {
    if (window.confirm('Вы уверены, что хотите отозвать задачу? Задача будет переведена в статус "На пересмотрении"!')) {
      recallTaskMutation.mutate()
    }
  }

  const deleteTaskMutation = useMutation({
    mutationFn: async () => {
      return api.delete(`/tasks/${id}/`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success('Задача успешно удалена')
      // Перенаправляем на список задач
      window.location.href = '/tasks'
    },
    onError: (error: any) => {
      alert(error?.response?.data?.error || 'Ошибка при удалении задачи')
    },
  })

  const handleDelete = () => {
    if (window.confirm('Вы уверены, что хотите удалить задачу? Это действие нельзя отменить.')) {
      deleteTaskMutation.mutate()
    }
  }

  const handleRedirect = () => {
    if (!selectedRedirectEmployeeId) {
      alert('Выберите нового исполнителя')
      return
    }
    redirectTaskMutation.mutate(selectedRedirectEmployeeId)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  // Проверяем ошибку доступа
  if (error && (error as Error).message === 'access_denied') {
    return (
      <div className="text-center py-12">
        <div className="max-w-md mx-auto">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">Доступ запрещен</h2>
          <p className="text-muted-foreground mb-6">
            У вас нет доступа к этой задаче. Вы можете просматривать только свои задачи или задачи, к которым у вас есть доступ.
          </p>
          <Button asChild>
            <Link to="/tasks">Вернуться к списку задач</Link>
          </Button>
        </div>
      </div>
    )
  }

  if (!task) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground mb-4">Задача не найдена</p>
        <Button asChild>
          <Link to="/tasks">Вернуться к списку</Link>
        </Button>
      </div>
    )
  }

  const isUrgent = task.due_date && new Date(task.due_date) <= new Date(Date.now() + 3 * 24 * 60 * 60 * 1000)

  // Проверяем, является ли текущий пользователь исполнителем задачи
  const isAssignedEmployee = user?.employee?.id && (
    task.assigned_employee?.id === user.employee.id
  )

  // Проверяем, может ли пользователь перенаправить задачу
  const canRedirect = isAssignedEmployee &&
    task.task_type === 'regular' &&
    currentUser?.employee?.role &&
    ['deputy', 'head'].includes(currentUser.employee.role) &&
    (task.status === 'new' || task.status === 'in_progress')

  // Вернуть задачу себе может тот, кто её перенаправил (только если ещё не принята в работу)
  const isRedirector = user?.employee?.id && task.redirected_by?.id === user.employee.id
  const canReturnRedirect = isRedirector &&
    task.task_type === 'regular' &&
    task.status === 'new'

  // Проверяем, может ли создатель редактировать или отозвать задачу
  const isCreator = user?.employee?.id && task.created_by?.id === user.employee.id
  // Редактирование доступно только для статуса revision
  const canEdit = isCreator && task.status === 'revision'
  // Отзыв доступен для:
  // 1. Статус send_for_approve
  // 2. Статус new и нет цепочки согласующих
  const hasApprovalChain = task.creation_approval_chain && task.creation_approval_chain.length > 0
  const canRecall = isCreator && (
    task.status === 'send_for_approve' || 
    (task.status === 'new' && !hasApprovalChain)
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/tasks">
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">{task.title}</h1>
          <div className="flex items-center gap-2 mt-2">
            {(task.task_type === 'approval' || task.task_type === 'review' || task.task_type === 'task_approval') && (
              <Badge variant="default" className="bg-blue-500">
                {task.task_type === 'approval' ? 'Согласование плана' : task.task_type === 'review' ? 'Проверка' : 'Согласование создания'}
              </Badge>
            )}
            <Badge className={statusColors[task.status]}>
              {statusLabels[task.status]}
            </Badge>
            {task.priority === 'urgent' && (
              <Badge variant="destructive">
                <AlertCircle className="w-3 h-3 mr-1" />
                Срочно
              </Badge>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-[3fr_2fr]">
        {/* Основная информация */}
        <Card>
          <CardHeader>
            <CardTitle>Информация</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {task.description && (
              <div>
                <h3 className="font-semibold mb-2 text-sm">Описание</h3>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">{task.description}</p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              {task.due_date && (
                <div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                    <Calendar className="w-4 h-4" />
                    <span>Срок выполнения</span>
                  </div>
                  <p className={isUrgent ? 'text-red-500 font-medium' : ''}>
                    {formatDateTimeInAstanaTime(task.due_date)}
                  </p>
                </div>
              )}

              <div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <Clock className="w-4 h-4" />
                  <span>Создано</span>
                </div>
                <p>{formatDateTimeInAstanaTime(task.created_at)}</p>
              </div>

              {task.created_by && (
                <div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                    <User className="w-4 h-4" />
                    <span>От:</span>
                  </div>
                  <p>
                    {task.created_by.full_name}
                  </p>
                </div>
              )}

              {task.assigned_employee && (
                <div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                    <User className="w-4 h-4" />
                    <span>Исполнитель:</span>
                  </div>
                  <p>
                    {task.assigned_employee.full_name}
                  </p>
                </div>
              )}

              {/* Перенаправляющие */}
              {(task.redirected_by || (task.redirect_chain_employees && task.redirect_chain_employees.length > 0)) && (
                <div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                    <Share2 className="w-4 h-4" />
                    <span>Перенаправлена от:</span>
                  </div>
                  {task.redirect_chain_employees && task.redirect_chain_employees.length > 0 ? (
                    <div className="space-y-1">
                      {task.redirect_chain_employees.map((redirector, idx) => (
                        <p key={redirector.id} className="text-sm">
                          {idx + 1}. {redirector.full_name}
                        </p>
                      ))}
                    </div>
                  ) : task.redirected_by ? (
                    <p>
                      {task.redirected_by.full_name}
                    </p>
                  ) : null}
                </div>
              )}

              {/* Проверяющий */}
              {(task.status === 'sent_for_review' || task.status === 'under_review') && task.current_reviewer && (
                <div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                    <FileText className="w-4 h-4" />
                    <span>Проверяет:</span>
                  </div>
                  <p>
                    {task.current_reviewer.full_name}
                  </p>
                </div>
              )}

              {/* Согласующий */}
              {task.status === 'send_for_approve' && task.current_approver && (
                <div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Согласует:</span>
                  </div>
                  <p>
                    {task.current_approver.full_name}
                  </p>
                </div>
              )}
            </div>

            {task.card && (
              <div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <FileText className="w-4 h-4" />
                  <span>Мероприятие</span>
                </div>
                <Link
                  to={`/cards/${task.card}`}
                  className="text-primary hover:underline"
                >
                  {task.card_title || `Мероприятие #${task.card}`}
                </Link>
              </div>
            )}

            {(task.attachments && task.attachments.length > 0) || task.google_drive_link ? (
              <div>
                <h3 className="font-semibold mb-2">Вложения</h3>
                <div className="space-y-2">
                  {/* Показываем старую Google Drive ссылку, если она есть (для обратной совместимости) */}
                  {task.google_drive_link && !task.attachments?.some(att => att.link === task.google_drive_link) && (
                    <div className="flex items-center gap-2 p-2 border rounded">
                      <a
                        href={task.google_drive_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 text-primary hover:underline"
                      >
                        <ExternalLink className="w-4 h-4" />
                        {task.google_drive_link}
                      </a>
                    </div>
                  )}
                  {/* Показываем вложения */}
                  {task.attachments && task.attachments.map((attachment) => (
                    <div key={attachment.id} className="flex items-center gap-2 p-2 border rounded">
                      {attachment.file ? (
                        <a
                          href={attachment.file}
                          download={attachment.file_name || undefined}
                          className="flex items-center gap-2 text-primary hover:underline"
                        >
                          <Paperclip className="w-4 h-4" />
                          {attachment.file_name || (() => {
                            try {
                              return decodeURIComponent(attachment.file.split('/').pop() || '')
                            } catch {
                              return attachment.file.split('/').pop() || 'Файл'
                            }
                          })()}
                        </a>
                      ) : (
                        <a
                          href={attachment.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 text-primary hover:underline"
                        >
                          <ExternalLink className="w-4 h-4" />
                          {attachment.link}
                        </a>
                      )}
                      {attachment.uploaded_by && (
                        <span className="text-xs text-muted-foreground ml-auto">
                          {attachment.uploaded_by.full_name}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {task.review_comment && (
              <div className="p-4 bg-blue-50 dark:bg-blue-950 rounded-lg">
                <h3 className="font-semibold mb-2">Комментарий проверяющего</h3>
                <p className="text-sm">{task.review_comment}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Действия */}
        <Card>
          <CardHeader>
            <CardTitle>Действия</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Для задач типа approval: сначала "Взять в работу", потом "Согласовать план" */}
            {task.task_type === 'approval' ? (
              <>
                {(task.status === 'new' || task.status === 'rejected') && isAssignedEmployee && (
                  <Button
                    onClick={() => takeTaskMutation.mutate()}
                    disabled={takeTaskMutation.isPending}
                    className="w-full"
                  >
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Взять в работу
                  </Button>
                )}
                {task.status === 'in_progress' && isAssignedEmployee && (
                  <Button
                    asChild
                    className="w-full bg-blue-500 hover:bg-blue-600"
                    variant="default"
                  >
                    <Link to={`/tasks/${id}/approve-plan`} className="flex items-center justify-center w-full">
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      Согласовать план
                    </Link>
                  </Button>
                )}
              </>
            ) : (
              <>
                {/* Для обычных задач */}
                {(task.status === 'new' || task.status === 'rejected') && isAssignedEmployee && (
                  <Button
                    onClick={() => takeTaskMutation.mutate()}
                    disabled={takeTaskMutation.isPending}
                    className="w-full"
                  >
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Взять в работу
                  </Button>
                )}

                {task.status === 'in_progress' && task.task_type === 'regular' && isAssignedEmployee && (
                  <Button
                    asChild
                    className="w-full"
                    variant="default"
                  >
                    <Link to={`/tasks/${id}/execute`} className="flex items-center justify-center w-full">
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      Выполнить
                    </Link>
                  </Button>
                )}

                {/* Вернуть задачу последнему перенаправившему (если ещё не принята в работу) */}
                {/* Вернуть задачу себе (доступно тому, кто перенаправил, если задача ещё не принята) */}
                {canReturnRedirect && (
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => {
                      if (window.confirm('Забрать задачу обратно к себе? Текущий исполнитель перестанет видеть её у себя.')) {
                        returnRedirectMutation.mutate()
                      }
                    }}
                    disabled={returnRedirectMutation.isPending}
                  >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    {returnRedirectMutation.isPending ? 'Возврат...' : 'Вернуть'}
                  </Button>
                )}

                {/* Кнопка перенаправления для заместителей и руководителей */}
                {canRedirect && (
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => setShowRedirectModal(true)}
                  >
                    <Share2 className="w-4 h-4 mr-2" />
                    Перенаправить
                  </Button>
                )}
              </>
            )}

            {task.status === 'sent_for_review' && task.task_type === 'regular' && isAssignedEmployee && (
              <Button
                asChild
                className="w-full"
                variant="outline"
              >
                <Link to={`/tasks/${id}/execute`} className="flex items-center justify-center">
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  Редактировать выполнение
                </Link>
              </Button>
            )}

            {task.status === 'in_progress' && task.task_type === 'review' && isAssignedEmployee && (
              <Button
                asChild
                className="w-full"
              >
                <Link to={`/tasks/${id}/review`} className="flex items-center justify-center w-full">
                  <FileText className="w-4 h-4 mr-2" />
                  Проверить выполнение
                </Link>
              </Button>
            )}

            {/* Для задач согласования создания - только ссылка на страницу согласования */}
            {task.task_type === 'task_approval' && task.status === 'in_progress' && isAssignedEmployee && (
              <Button
                asChild
                className="w-full"
                variant="default"
              >
                <Link to={`/tasks/${id}/creation-approval`} className="flex items-center justify-center w-full">
                  <FileText className="w-4 h-4 mr-2" />
                  Посмотреть задачу
                </Link>
              </Button>
            )}

            {/* Кнопка отзыва для создателя задачи в статусе send_for_approve */}
            {canRecall && (
              <Button
                variant="outline"
                className="w-full"
                onClick={handleRecall}
                disabled={recallTaskMutation.isPending}
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                {recallTaskMutation.isPending ? 'Отзыв...' : 'Отозвать задачу'}
              </Button>
            )}

            {/* Кнопка редактирования для создателя задачи в статусе revision */}
            {canEdit && (
              <>
                <Button
                  asChild
                  variant="default"
                  className="w-full"
                >
                  <Link to={`/tasks/${id}/edit`} className="flex items-center justify-center w-full">
                    <Edit className="w-4 h-4 mr-2" />
                    Редактировать задачу
                  </Link>
                </Button>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={handleDelete}
                  disabled={deleteTaskMutation.isPending}
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  {deleteTaskMutation.isPending ? 'Удаление...' : 'Удалить задачу'}
                </Button>
              </>
            )}

            {/* Кнопка открытия мероприятия */}
            {task.card && (
              <Button asChild variant="outline" className="w-full">
                <Link to={`/cards/${task.card}`} className="flex items-center justify-center w-full">
                  <FileText className="w-4 h-4 mr-2" />
                  Открыть мероприятие
                </Link>
              </Button>
            )}

            {task.history && task.history.length > 0 && (
              <Button 
                variant="outline" 
                className="w-full"
                onClick={() => setShowHistoryModal(true)}
              >
                <History className="w-4 h-4 mr-2" />
                История действий
              </Button>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Модальное окно истории действий */}
      {task.history && task.history.length > 0 && (
        <Dialog 
          open={showHistoryModal} 
          onOpenChange={setShowHistoryModal}
          centered
          maxWidth="xl"
        >
          <DialogContent onClose={() => setShowHistoryModal(false)}>
            <div className="max-w-2xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>История действий</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-4">
              {task.history.map((item) => {
                const actionColor = historyActionColors[item.action] || 'bg-primary'
                return (
                  <div key={item.id} className="flex items-start gap-3 pb-4 border-b last:border-0">
                    <div className={`w-2 h-2 rounded-full ${actionColor} mt-2 flex-shrink-0`} />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium">{item.action_display || item.action}</p>
                    {item.employee && (
                      <p className="text-sm text-muted-foreground mt-1">
                        {item.employee.full_name}
                      </p>
                    )}
                    {item.comment && (
                      <p className="text-sm text-muted-foreground mt-2 p-2 bg-muted rounded">
                        {item.comment}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground mt-2">
                      {formatDateTimeInAstanaTime(item.timestamp)}
                    </p>
                  </div>
                </div>
                )
              })}
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Модальное окно перенаправления задачи */}
      <Dialog 
        open={showRedirectModal} 
        onOpenChange={setShowRedirectModal}
        centered
        maxWidth="md"
      >
        <DialogContent onClose={() => {
          setShowRedirectModal(false)
          setSelectedRedirectEmployeeId(null)
        }}>
          <DialogHeader>
            <DialogTitle>Перенаправить задачу</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <div className="mb-4">
              <label className="text-sm font-medium mb-2 block">
                Новый исполнитель <span className="text-red-500">*</span>
              </label>
              <select
                value={selectedRedirectEmployeeId?.toString() || ''}
                onChange={(e) => setSelectedRedirectEmployeeId(e.target.value ? parseInt(e.target.value) : null)}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                <option value="">Выберите сотрудника</option>
                {availableEmployeesForRedirect.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.full_name}
                    {emp.position && ` (${emp.position})`}
                    {emp.department && ` - ${emp.department.name}`}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setShowRedirectModal(false)
                  setSelectedRedirectEmployeeId(null)
                }}
              >
                Отмена
              </Button>
              <Button
                onClick={handleRedirect}
                disabled={redirectTaskMutation.isPending || !selectedRedirectEmployeeId}
              >
                {redirectTaskMutation.isPending ? 'Перенаправление...' : 'Перенаправить'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

    </div>
  )
}
