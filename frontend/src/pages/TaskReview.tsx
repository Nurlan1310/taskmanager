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
  AlertCircle
} from 'lucide-react'
import { formatDateTimeInAstanaTime } from '@/lib/dateUtils'
import { Task, TaskAttachment } from '@/types/task'
import { toast } from 'sonner'

interface ReviewData {
  review_task: Task
  base_task: Task
  attachments: TaskAttachment[]
  last_exec_comment: string | null
}

export default function TaskReview() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  
  const [comment, setComment] = useState('')

  const { data: reviewData, isLoading } = useQuery<ReviewData>({
    queryKey: ['taskReview', id],
    queryFn: async () => {
      const response = await api.get(`/tasks/${id}/review/`)
      return response.data
    },
  })

  const takeTaskMutation = useMutation({
    mutationFn: async () => {
      return api.post(`/tasks/${id}/take/`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['taskReview', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const approveMutation = useMutation({
    mutationFn: async (comment: string) => {
      return api.post(`/tasks/${id}/review/approve/`, { comment })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['taskReview', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success('Исполнение задачи утверждено')
      navigate('/tasks')
    },
  })

  const rejectMutation = useMutation({
    mutationFn: async (comment: string) => {
      return api.post(`/tasks/${id}/review/reject/`, { comment })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['taskReview', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success('Исполнение задачи отправлено на доработку')
      navigate('/tasks')
    },
  })

  const handleApprove = () => {
    approveMutation.mutate(comment)
  }

  const handleReject = () => {
    if (!comment.trim()) {
      alert('Укажите причину возврата на доработку')
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

  if (!reviewData) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground mb-4">Данные не найдены</p>
        <Button asChild>
          <Link to="/tasks">Вернуться к списку</Link>
        </Button>
      </div>
    )
  }

  const { review_task, base_task, attachments, last_exec_comment } = reviewData

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/tasks">
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">Проверка выполнения задачи</h1>
          <p className="text-muted-foreground mt-2">{base_task.title}</p>
        </div>
      </div>

      {/* Информация о задаче */}
      <Card>
        <CardHeader>
          <CardTitle>Информация о задаче</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {base_task.description && (
            <div>
              <h3 className="font-semibold mb-2">Описание</h3>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {base_task.description}
              </p>
            </div>
          )}

          {base_task.assigned_employee && (
            <div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <User className="w-4 h-4" />
                <span>Исполнитель</span>
              </div>
              <p>
                {base_task.assigned_employee.full_name}
                {base_task.assigned_employee.position && ` (${base_task.assigned_employee.position})`}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Комментарий исполнителя */}
      <Card>
        <CardHeader>
          <CardTitle>Комментарий исполнителя</CardTitle>
        </CardHeader>
        <CardContent>
          {last_exec_comment ? (
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm whitespace-pre-wrap">{last_exec_comment}</p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Нет комментария исполнителя</p>
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
      {review_task.status === 'new' && (
        <Card>
          <CardContent className="py-6">
            <div className="text-center space-y-4">
              <p className="text-muted-foreground">
                Для начала проверки необходимо взять задачу в работу
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

      {review_task.status === 'in_progress' && (
        <Card>
          <CardHeader>
            <CardTitle>Решение по проверке</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">
                Комментарий при проверке
              </label>
              <Textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Комментарий (виден исполнителю)..."
                rows={4}
              />
              <p className="text-xs text-muted-foreground mt-1">
                При возврате на доработку комментарий обязателен
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
                {approveMutation.isPending ? 'Утверждение...' : 'Утвердить'}
              </Button>
              <Button
                onClick={handleReject}
                disabled={rejectMutation.isPending || !comment.trim()}
                variant="destructive"
                className="flex-1"
              >
                <XCircle className="w-4 h-4 mr-2" />
                {rejectMutation.isPending ? 'Возврат...' : 'Вернуть на доработку'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {review_task.status === 'done' && (
        <Card>
          <CardContent className="py-6">
            <div className="text-center">
              <p className="text-muted-foreground mb-4">
                Проверка завершена. Дальнейшие действия недоступны.
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

