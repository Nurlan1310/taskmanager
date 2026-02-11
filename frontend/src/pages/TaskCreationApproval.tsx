import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { 
  ArrowLeft, 
  User, 
  FileText, 
  ExternalLink,
  Paperclip,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Calendar
} from 'lucide-react'
import { formatDateTimeInAstanaTime } from '@/lib/dateUtils'
import { Task, TaskAttachment } from '@/types/task'

interface ApprovalData {
  approval_task: Task
  main_task: Task
  attachments: TaskAttachment[]
}

export default function TaskCreationApproval() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  
  const [comment, setComment] = useState('')

  const { data: approvalData, isLoading } = useQuery<ApprovalData>({
    queryKey: ['taskCreationApproval', id],
    queryFn: async () => {
      const response = await api.get(`/tasks/${id}/creation-approval/`)
      return response.data
    },
  })

  const takeTaskMutation = useMutation({
    mutationFn: async () => {
      return api.post(`/tasks/${id}/take/`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['taskCreationApproval', id] })
      queryClient.invalidateQueries({ queryKey: ['task', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })

  const approveMutation = useMutation({
    mutationFn: async (comment: string) => {
      return api.post(`/tasks/${id}/approve-creation/`, { comment })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['taskCreationApproval', id] })
      queryClient.invalidateQueries({ queryKey: ['task', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      navigate('/tasks')
    },
  })

  const rejectMutation = useMutation({
    mutationFn: async (comment: string) => {
      return api.post(`/tasks/${id}/reject-creation/`, { comment })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['taskCreationApproval', id] })
      queryClient.invalidateQueries({ queryKey: ['task', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      navigate('/tasks')
    },
  })

  const handleApprove = () => {
    approveMutation.mutate(comment)
  }

  const handleReject = () => {
    if (!comment.trim()) {
      alert('Укажите причину отклонения')
      return
    }
    rejectMutation.mutate(comment)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!approvalData) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground mb-4">Данные не найдены</p>
        <Button asChild>
          <Link to="/tasks">Вернуться к списку</Link>
        </Button>
      </div>
    )
  }

  const { approval_task, main_task, attachments } = approvalData

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to={`/tasks/${id}`}>
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">Согласование создания задачи</h1>
        </div>
      </div>

      {/* Информация о задаче */}
      <Card>
        <CardHeader>
          <CardTitle>Информация о задаче</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h3 className="font-semibold mb-2">Название задачи</h3>
            <p className="text-lg">{main_task.title}</p>
          </div>
          {main_task.description && (
            <div>
              <h3 className="font-semibold mb-2">Описание</h3>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {main_task.description}
              </p>
            </div>
          )}

          {main_task.due_date && (
            <div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <Calendar className="w-4 h-4" />
                <span>Срок выполнения</span>
              </div>
              <p>{formatDateTimeInAstanaTime(main_task.due_date)}</p>
            </div>
          )}

          {main_task.created_by && (
            <div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <User className="w-4 h-4" />
                <span>Создатель</span>
              </div>
              <p>
                {main_task.created_by.full_name}
                {main_task.created_by.position && ` (${main_task.created_by.position})`}
              </p>
            </div>
          )}

          {main_task.recipients && main_task.recipients.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <User className="w-4 h-4" />
                <span>Адресаты</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {main_task.recipients.map((recipient) => (
                  <span key={recipient.id} className="text-sm">
                    {recipient.full_name}
                    {recipient.position && ` (${recipient.position})`}
                  </span>
                ))}
              </div>
            </div>
          )}

          {main_task.priority && (
            <div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <span>Приоритет</span>
              </div>
              <p className="text-sm">
                {main_task.priority === 'urgent' ? 'Срочная' : 'Обычная'}
              </p>
            </div>
          )}

          {main_task.is_according_to_plan !== undefined && (
            <div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <span>Тип создания</span>
              </div>
              <p className="text-sm">
                {main_task.is_according_to_plan ? 'Согласно плана' : 'Не согласно плана'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Вложения */}
      <Card>
        <CardHeader>
          <CardTitle>Вложения</CardTitle>
        </CardHeader>
        <CardContent>
          {attachments && attachments.length > 0 ? (
            <div className="space-y-3">
              {attachments.map((attachment) => (
                <div key={attachment.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    {attachment.file ? (
                      <>
                        <Paperclip className="w-5 h-5 text-muted-foreground" />
                        <a
                          href={attachment.file}
                          download={attachment.file_name || undefined}
                          className="text-primary hover:underline flex items-center gap-2"
                        >
                          <FileText className="w-4 h-4" />
                          {attachment.file_name || (() => {
                            try {
                              return decodeURIComponent(attachment.file.split('/').pop() || '')
                            } catch {
                              return attachment.file.split('/').pop() || 'Файл'
                            }
                          })()}
                        </a>
                      </>
                    ) : (
                      <>
                        <ExternalLink className="w-5 h-5 text-muted-foreground" />
                        <a
                          href={attachment.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:underline flex items-center gap-2"
                        >
                          <ExternalLink className="w-4 h-4" />
                          {attachment.link}
                        </a>
                      </>
                    )}
                  </div>
                  {attachment.uploaded_at && (
                    <span className="text-xs text-muted-foreground">
                      {formatDateTimeInAstanaTime(attachment.uploaded_at)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Нет приложенных файлов или ссылок</p>
          )}
        </CardContent>
      </Card>

      {/* Действия */}
      {approval_task.status === 'new' && (
        <Card>
          <CardContent className="py-6">
            <div className="text-center space-y-4">
              <p className="text-muted-foreground">
                Для начала согласования необходимо взять задачу в работу
              </p>
              <Button
                onClick={() => takeTaskMutation.mutate()}
                disabled={takeTaskMutation.isPending}
                className="w-full md:w-auto"
              >
                <AlertCircle className="w-4 h-4 mr-2" />
                {takeTaskMutation.isPending ? 'Принятие...' : 'Взять в работу'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {approval_task.status === 'in_progress' && (
        <>
        

          <Card>
            <CardHeader>
              <CardTitle>Решение по согласованию</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Комментарий
                </label>
                <Textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Комментарий (обязателен при отклонении)..."
                  rows={4}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  При отклонении комментарий обязателен
                </p>
              </div>

              <div className="flex gap-4">
                <Button
                  onClick={handleApprove}
                  disabled={approveMutation.isPending}
                  variant="default"
                  className="flex-1"
                >
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  {approveMutation.isPending ? 'Согласование...' : 'Согласовать'}
                </Button>
                <Button
                  onClick={handleReject}
                  disabled={rejectMutation.isPending || !comment.trim()}
                  variant="destructive"
                  className="flex-1"
                >
                  <XCircle className="w-4 h-4 mr-2" />
                  {rejectMutation.isPending ? 'Отклонение...' : 'Отклонить'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {approval_task.status === 'done' && main_task.status === 'revision' && (
        <Card>
          <CardContent className="py-6">
            <div className="text-center">
              <p className="text-muted-foreground mb-4">
                Создание задачи отклонено. Дальнейшие действия недоступны.
              </p>
              <Button asChild variant="outline">
                <Link to="/tasks">Вернуться к списку задач</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {approval_task.status === 'done' && main_task.status !== 'revision' && (
        <Card>
          <CardContent className="py-6">
            <div className="text-center">
              <p className="text-muted-foreground mb-4">
                Согласование завершено. Дальнейшие действия недоступны.
              </p>
              <Button asChild variant="outline">
                <Link to="/tasks">Вернуться к списку задач</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
