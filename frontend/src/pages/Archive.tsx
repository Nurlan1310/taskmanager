import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useSearchParams } from 'react-router-dom'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { Calendar, Building2 } from 'lucide-react'
import { formatDateInAstanaTime } from '@/lib/dateUtils'

interface EventCard {
  id: number
  title: string
  description?: string
  start_date: string
  end_date?: string
  created_by: {
    user: {
      first_name: string
      last_name: string
    }
  }
  responsible_department?: {
    id: number
    name: string
  }
  progress: number
  approval_count: number
  urgent_count: number
  other_count: number
  done_count?: number
  total_tasks?: number
  user_active_count?: number
  user_urgent_count?: number
  user_approval_count?: number
  user_total_tasks?: number
  user_done_tasks?: number
  categories: Array<{ id: number; name: string; slug: string }>
  has_plan?: boolean
  plan_status?: 'draft' | 'pending' | 'rejected' | 'approved'
  visible?: boolean
  is_active?: boolean
}

interface Category {
  id: number
  name: string
  slug: string
}

export default function Archive() {
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedCategory = searchParams.get('category') || ''

  const { data: categories } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: async () => {
      const response = await api.get('/categories/')
      return Array.isArray(response.data) ? response.data : (response.data.results || [])
    },
  })

  const { data: cards, isLoading } = useQuery<EventCard[]>({
    queryKey: ['cards', 'archive', selectedCategory],
    queryFn: async () => {
      const url = selectedCategory 
        ? `/cards/?archive=true&category=${selectedCategory}`
        : '/cards/?archive=true'
      const response = await api.get(url)
      return Array.isArray(response.data) ? response.data : (response.data.results || [])
    },
  })

  const handleCategoryChange = (categorySlug: string) => {
    if (categorySlug) {
      setSearchParams({ category: categorySlug })
    } else {
      setSearchParams({})
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Архив мероприятий</h1>
          <p className="text-muted-foreground mt-2">
            Завершенные мероприятия
          </p>
        </div>
      </div>

      {/* Фильтр по категориям */}
      {categories && categories.length > 0 && (
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium">Категория:</label>
          <Select
            value={selectedCategory}
            onChange={(e) => handleCategoryChange(e.target.value)}
            className="w-64"
          >
            <option value="">Все</option>
            {categories.map((category) => (
              <option key={category.id} value={category.slug}>
                {category.name}
              </option>
            ))}
          </Select>
          {(() => {
            const internalCategory = categories.find(cat => 
              cat.name.toLowerCase().includes('внутренн') || 
              cat.slug.toLowerCase().includes('internal') ||
              cat.slug.toLowerCase().includes('vnutrennyaya')
            )
            return internalCategory ? (
              <Button
                variant={selectedCategory === internalCategory.slug ? 'default' : 'outline'}
                size="sm"
                onClick={() => {
                  if (selectedCategory === internalCategory.slug) {
                    handleCategoryChange('')
                  } else {
                    handleCategoryChange(internalCategory.slug)
                  }
                }}
              >
                Внутренняя работа
              </Button>
            ) : null
          })()}
        </div>
      )}

      {cards && cards.length > 0 ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {cards.map((card) => (
            <Card key={card.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <CardTitle className="text-xl">
                    <Link
                      to={`/cards/${card.id}`}
                      className="hover:text-primary transition-colors"
                    >
                      {card.title}
                    </Link>
                  </CardTitle>
                </div>
                <div className="flex flex-wrap gap-2 mt-2">
                  {card.categories && card.categories.length > 0 && card.categories.map((cat) => (
                    <Badge key={cat.id} variant="secondary">
                      {cat.name}
                    </Badge>
                  ))}
                  {card.has_plan && card.plan_status !== 'approved' && (
                    <Badge 
                      variant={
                        card.plan_status === 'pending' ? 'default' :
                        card.plan_status === 'rejected' ? 'destructive' :
                        'secondary'
                      }
                      className={
                        card.plan_status === 'pending' ? 'bg-yellow-500' :
                        card.plan_status === 'rejected' ? 'bg-red-500' :
                        ''
                      }
                    >
                      {card.plan_status === 'pending' ? 'На согласовании' :
                       card.plan_status === 'rejected' ? 'План отклонён' :
                       'Черновик'}
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 mb-4">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Calendar className="w-4 h-4" />
                    <span>
                      {formatDateInAstanaTime(card.start_date)}
                      {card.end_date && ` — ${formatDateInAstanaTime(card.end_date)}`}
                    </span>
                  </div>
                  {card.responsible_department && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Building2 className="w-4 h-4" />
                      <span>
                        {card.responsible_department.name}
                      </span>
                    </div>
                  )}
                </div>

                {/* Прогресс */}
                <div className="mb-4">
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-muted-foreground">Прогресс</span>
                    <span className="font-semibold">
                      {card.done_count || 0}/{card.total_tasks || 0} ({Math.round(card.progress || 0)}%)
                    </span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div
                      className="bg-primary rounded-full h-2 transition-all"
                      style={{ width: `${Math.round(card.progress || 0)}%` }}
                    />
                  </div>
                </div>

                {/* Счётчики задач пользователя */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {(card.user_active_count || 0) > 0 && (
                    <Badge variant="secondary">
                      Активные: {card.user_active_count}
                    </Badge>
                  )}
                  {(card.user_urgent_count || 0) > 0 && (
                    <Badge variant="destructive">
                      Срочные: {card.user_urgent_count}
                    </Badge>
                  )}
                  {(card.user_approval_count || 0) > 0 && (
                    <Badge variant="default" className="bg-blue-500">
                      Согласования: {card.user_approval_count}
                    </Badge>
                  )}
                </div>

                <Button asChild variant="outline" className="w-full">
                  <Link to={`/cards/${card.id}`}>
                    Открыть мероприятие
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">В архиве пока нет мероприятий</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

