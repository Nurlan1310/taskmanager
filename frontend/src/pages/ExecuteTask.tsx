import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Task } from '@/types/task'
import { ArrowLeft, Save, X } from 'lucide-react'
import { toast } from 'sonner'

export default function ExecuteTask() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  
  const [executionComment, setExecutionComment] = useState('')
  const [link, setLink] = useState('')
  const [file, setFile] = useState<File | null>(null)

  const { data: task, isLoading } = useQuery<Task>({
    queryKey: ['task', id],
    queryFn: async () => {
      const response = await api.get(`/tasks/${id}/`)
      return response.data
    },
  })

  const executeTaskMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      const response = await api.post(`/tasks/${id}/execute/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      return response.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['task', id] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      if (data?.status === 'done') {
        toast.success('Задача выполнена без проверки')
      } else {
        toast.success('Исполнение задачи отправлено на проверку')
      }
      navigate(`/tasks/${id}`)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    const formData = new FormData()
    if (executionComment) {
      formData.append('execution_comment', executionComment)
    }
    if (link) {
      formData.append('link', link)
    }
    if (file) {
      formData.append('file', file)
    }

    executeTaskMutation.mutate(formData)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
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

  // Проверяем, можно ли редактировать выполнение
  const canEdit = task.status === 'sent_for_review' || task.status === 'in_progress'
  const isEditing = task.status === 'sent_for_review'

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to={`/tasks/${id}`}>
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">
            {isEditing ? 'Редактирование выполнения' : 'Исполнение задачи'}
          </h1>
          <p className="text-muted-foreground mt-2">{task.title}</p>
        </div>
      </div>

      {!canEdit ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground mb-4">
              Задача уже на рассмотрении и не может быть изменена
            </p>
            <Button asChild>
              <Link to={`/tasks/${id}`}>Вернуться к задаче</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>
              {isEditing ? 'Редактирование информации о выполнении' : 'Информация о выполнении'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="text-sm font-medium mb-2 block">
                Комментарий о выполнении
              </label>
              <Textarea
                value={executionComment}
                onChange={(e) => setExecutionComment(e.target.value)}
                placeholder="Опишите, что сделано..."
                rows={6}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">
                Ссылка (Google Диск и т.д.)
              </label>
              <Input
                type="url"
                value={link}
                onChange={(e) => setLink(e.target.value)}
                placeholder="https://..."
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">
                Вложение (файл)
              </label>
              <div className="flex items-center gap-4">
                <Input
                  type="file"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="flex-1"
                />
                {file && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">{file.name}</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => setFile(null)}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-4">
              <Button 
                type="submit" 
                disabled={executeTaskMutation.isPending || (!isEditing && !executionComment && !link && !file)}
                className="flex-1"
              >
                <Save className="w-4 h-4 mr-2" />
                {executeTaskMutation.isPending 
                  ? 'Отправка...' 
                  : isEditing 
                    ? 'Обновить выполнение' 
                    : 'Отправить на согласование'}
              </Button>
              <Button type="button" variant="outline" asChild>
                <Link to={`/tasks/${id}`}>Отмена</Link>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
      )}
    </div>
  )
}

