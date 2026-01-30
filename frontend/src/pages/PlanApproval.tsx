import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { toast } from 'sonner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, CheckCircle2, XCircle, FileText, User, Calendar } from 'lucide-react'
import { Task, EventCard } from '@/types/task'
import { formatDateInAstanaTime } from '@/lib/dateUtils'

interface PlanApprovalData {
  task: Task
  card: EventCard
  approvers: Array<{
    id: number
    employee: { 
      id: number
      full_name?: string
      user: { first_name: string; last_name: string }
    }
    order: number
  }>
  current_approver_index: number
}

export default function PlanApproval() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [rejectReason, setRejectReason] = useState('')
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [correctedPlanFile, setCorrectedPlanFile] = useState<File | null>(null)

  const { data: approvalData, isLoading, isError, error } = useQuery<PlanApprovalData>({
    queryKey: ['planApproval', id],
    queryFn: async () => {
      const response = await api.get(`/tasks/${id}/`)
      const task = response.data
      
      if (!task.card) {
        throw new Error('У задачи не указана карточка')
      }
      
      // Получаем информацию о карточке
      const cardResponse = await api.get(`/cards/${task.card}/`)
      const card = cardResponse.data
      
      // Получаем информацию о согласующих
      let approvers = []
      try {
        const approversResponse = await api.get(`/cards/${task.card}/approvers/`)
        approvers = approversResponse.data || []
      } catch (err) {
        // Если endpoint не найден, используем данные из card.approvers
        if (card.approvers && Array.isArray(card.approvers)) {
          approvers = card.approvers.map((emp: any, index: number) => ({
            id: index,
            employee: emp,
            order: index
          }))
        }
      }
      
      return {
        task,
        card,
        approvers,
        current_approver_index: card.current_approver_index || 0
      }
    },
  })

  const approveMutation = useMutation({
    mutationFn: async () => {
      return api.post(`/tasks/${id}/approve-plan/`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['planApproval', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      queryClient.invalidateQueries({ queryKey: ['cards'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success('План мероприятия согласован')
      navigate(`/cards/${approvalData?.card.id}`)
    },
    onError: (error: any) => {
      alert(`Ошибка при утверждении плана: ${error.response?.data?.error || error.message}`)
    },
  })

  const rejectMutation = useMutation({
    mutationFn: async (data: { reason: string; correctedPlanFile?: File | null }) => {
      const formData = new FormData()
      formData.append('reason', data.reason)
      if (data.correctedPlanFile) {
        formData.append('corrected_plan_file', data.correctedPlanFile)
      }
      return api.post(`/tasks/${id}/reject-plan/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['planApproval', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      queryClient.invalidateQueries({ queryKey: ['cards'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success('План мероприятия отклонен')
      navigate(`/cards/${approvalData?.card.id}`)
    },
    onError: (error: any) => {
      alert(`Ошибка при отклонении плана: ${error.response?.data?.error || error.message}`)
    },
  })

  const handleApprove = () => {
    if (window.confirm('Вы уверены, что хотите согласовать этот план?')) {
      approveMutation.mutate()
    }
  }

  const handleReject = () => {
    if (!rejectReason.trim()) {
      alert('Пожалуйста, укажите причину отклонения')
      return
    }
    if (window.confirm('Вы уверены, что хотите отклонить этот план?')) {
      rejectMutation.mutate({ reason: rejectReason, correctedPlanFile })
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500 mb-4">Ошибка: {error?.message || 'Не удалось загрузить данные'}</p>
        <Button asChild>
          <Link to="/tasks">Вернуться к списку задач</Link>
        </Button>
      </div>
    )
  }

  if (!approvalData || !approvalData.task || !approvalData.card) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground mb-4">Данные не найдены</p>
        <Button asChild>
          <Link to="/tasks">Вернуться к списку задач</Link>
        </Button>
      </div>
    )
  }

  const { task, card, approvers, current_approver_index } = approvalData
  const isFinalApprover = card.final_approver && task.assigned_employee?.id === card.final_approver.id

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to={`/tasks/${id}`}>
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">Согласование плана мероприятия</h1>
          <p className="text-muted-foreground mt-1">
            {card.title}
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Информация о мероприятии</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h3 className="font-semibold mb-2">Название</h3>
            <p>{card.title}</p>
          </div>

          {card.description && (
            <div>
              <h3 className="font-semibold mb-2">Описание</h3>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">{card.description}</p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="w-4 h-4 text-muted-foreground" />
              <span className="text-muted-foreground">Период:</span>
              <span>
                {formatDateInAstanaTime(card.start_date)}
                {card.end_date && ` — ${formatDateInAstanaTime(card.end_date)}`}
              </span>
            </div>

            {card.responsible_department && (
              <div className="flex items-center gap-2 text-sm">
                <User className="w-4 h-4 text-muted-foreground" />
                <span className="text-muted-foreground">Ответственный отдел:</span>
                <span>{card.responsible_department.name}</span>
              </div>
            )}
          </div>

          {card.plan_file && (
            <div>
              <h3 className="font-semibold mb-2">План мероприятия</h3>
              <a
                href={`/api/cards/${card.id}/download-plan/`}
                rel="noopener noreferrer"
                className="text-primary hover:underline flex items-center gap-2"
              >
                <FileText className="w-4 h-4" />
                Скачать план мероприятия
              </a>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Процесс согласования</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {approvers.length === 0 && !card.final_approver && (
              <p className="text-sm text-muted-foreground text-center py-4">
                Согласующие не назначены
              </p>
            )}
            {approvers.map((approver, index) => {
              const isCurrent = index === current_approver_index
              const isCompleted = index < current_approver_index
              
              return (
                <div
                  key={approver.id}
                  className={`flex items-center gap-3 p-3 rounded-lg border ${
                    isCurrent ? 'bg-blue-50 dark:bg-blue-950 border-blue-500' :
                    isCompleted ? 'bg-green-50 dark:bg-green-950 border-green-500' :
                    'bg-gray-50 dark:bg-gray-900'
                  }`}
                >
                  <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-white dark:bg-gray-800">
                    {isCompleted ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500" />
                    ) : isCurrent ? (
                      <span className="text-blue-500 font-bold">{index + 1}</span>
                    ) : (
                      <span className="text-gray-400">{index + 1}</span>
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">
                      {approver.employee.full_name || `${approver.employee.user.first_name} ${approver.employee.user.last_name}`}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {isCompleted ? 'Согласовано' : isCurrent ? 'Текущий согласующий' : 'Ожидает согласования'}
                    </p>
                  </div>
                  {isCurrent && (
                    <Badge variant="default" className="bg-blue-500">
                      Текущий
                    </Badge>
                  )}
                </div>
              )
            })}

            {card.final_approver && (
              <div
                className={`flex items-center gap-3 p-3 rounded-lg border ${
                  current_approver_index >= approvers.length
                    ? 'bg-blue-50 dark:bg-blue-950 border-blue-500'
                    : approvers.length === 0 && current_approver_index === 0
                    ? 'bg-blue-50 dark:bg-blue-950 border-blue-500'
                    : 'bg-gray-50 dark:bg-gray-900'
                }`}
              >
                <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-white dark:bg-gray-800">
                  {card.plan_status === 'approved' ? (
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                  ) : (
                    <span className="text-blue-500 font-bold">✓</span>
                  )}
                </div>
                <div className="flex-1">
                  <p className="font-medium">
                    {((card.final_approver as any)?.full_name) || `${card.final_approver.user.first_name} ${card.final_approver.user.last_name}`}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {card.plan_status === 'approved' ? 'Утверждено' : 'Финальный утверждающий'}
                  </p>
                </div>
                {isFinalApprover && (
                  <Badge variant="default" className="bg-blue-500">
                    Текущий
                  </Badge>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {card.plan_rejected_reason && (
        <Card className="border-red-500">
          <CardHeader>
            <CardTitle className="text-red-500">План отклонён</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm">{card.plan_rejected_reason}</p>
          </CardContent>
        </Card>
      )}

      {task.status !== 'done' && task.status !== 'rejected' && (
        <Card>
          <CardHeader>
            <CardTitle>Решение по согласованию</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {!showRejectForm ? (
              <div className="flex gap-4">
                <Button
                  onClick={handleApprove}
                  disabled={approveMutation.isPending}
                  variant="default"
                  className="flex-1"
                >
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  {approveMutation.isPending ? 'Согласование...' : (isFinalApprover ? 'Утвердить' : 'Согласовать')}
                </Button>
                <Button
                  onClick={() => setShowRejectForm(true)}
                  disabled={approveMutation.isPending}
                  variant="destructive"
                  className="flex-1"
                >
                  <XCircle className="w-4 h-4 mr-2" />
                  Отклонить план
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Причина отклонения <span className="text-red-500">*</span>
                  </label>
                  <Textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Укажите причину отклонения плана..."
                    rows={4}
                    required
                  />
                </div>
                
                <div className="flex gap-4">
                  <Button
                    onClick={handleReject}
                    disabled={rejectMutation.isPending || !rejectReason.trim()}
                    variant="destructive"
                    className="flex-1"
                  >
                    <XCircle className="w-4 h-4 mr-2" />
                    {rejectMutation.isPending ? 'Отклонение...' : 'Отклонить'}
                  </Button>
                  <Button
                    onClick={() => {
                      setShowRejectForm(false)
                      setRejectReason('')
                      setCorrectedPlanFile(null)
                    }}
                    variant="outline"
                    className="flex-1"
                  >
                    Отмена
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {task.status === 'done' && (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-2" />
              <p className="font-semibold text-green-500">
                {isFinalApprover ? 'План утверждён' : 'План согласован'}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

