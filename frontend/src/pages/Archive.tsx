import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useSearchParams } from 'react-router-dom'
import api from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { Calendar, Building2, ChevronLeft, ChevronRight } from 'lucide-react'
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

type ScopeFilter = 'all' | 'my_department'

interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export default function Archive() {
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedCategory = searchParams.get('category') || ''
  const selectedScope = (searchParams.get('scope') as ScopeFilter) || 'all'
  const selectedDepartmentId = searchParams.get('department') || ''
  const currentPage = Math.max(parseInt(searchParams.get('page') || '1', 10) || 1, 1)

  const { data: currentUser } = useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const response = await api.get('/auth/me/')
      return response.data
    },
  })

  const isDirectorOrDeputy = currentUser?.employee?.role === 'director' || currentUser?.employee?.role === 'deputy'

  const { data: categories } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: async () => {
      const response = await api.get('/categories/')
      return Array.isArray(response.data) ? response.data : (response.data.results || [])
    },
  })

  const { data: departments } = useQuery({
    queryKey: ['departments'],
    queryFn: async () => {
      const response = await api.get('/departments/')
      const depts = Array.isArray(response.data) ? response.data : (response.data.results || [])
      return depts.sort((a: any, b: any) => {
        const pa = a.priority ?? 999
        const pb = b.priority ?? 999
        if (pa !== pb) return pa - pb
        return (a.name || '').localeCompare(b.name || '', 'ru')
      })
    },
    enabled: isDirectorOrDeputy,
  })

  const { data: cardsData, isLoading } = useQuery<PaginatedResponse<EventCard>>({
    queryKey: ['cards', 'archive', selectedCategory, selectedScope, selectedDepartmentId, currentPage],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.set('archive', 'true')
      params.set('page', currentPage.toString())
      if (selectedCategory) params.set('category', selectedCategory)
      if (selectedScope === 'my_department') params.set('scope', 'my_department')
      if (selectedDepartmentId && isDirectorOrDeputy) params.set('department_id', selectedDepartmentId)
      const response = await api.get(`/cards/?${params.toString()}`)
      if (Array.isArray(response.data)) {
        return {
          results: response.data,
          count: response.data.length,
          next: null,
          previous: null,
        }
      }
      return {
        results: response.data.results || [],
        count: response.data.count || 0,
        next: response.data.next || null,
        previous: response.data.previous || null,
      }
    },
  })

  const cards = cardsData?.results || []
  const totalCount = cardsData?.count || 0
  const hasNext = !!cardsData?.next
  const hasPrevious = !!cardsData?.previous
  const totalPages = Math.max(Math.ceil(totalCount / 24), 1)

  const handleCategoryChange = (categorySlug: string) => {
    const next = new URLSearchParams(searchParams)
    if (categorySlug) next.set('category', categorySlug)
    else next.delete('category')
    next.delete('page')
    setSearchParams(next)
  }

  const handleScopeChange = (scope: ScopeFilter) => {
    const next = new URLSearchParams(searchParams)
    if (scope === 'my_department') next.set('scope', 'my_department')
    else next.delete('scope')
    next.delete('page')
    setSearchParams(next)
  }

  const handleDepartmentChange = (departmentId: string) => {
    const next = new URLSearchParams(searchParams)
    if (departmentId) next.set('department', departmentId)
    else next.delete('department')
    next.delete('page')
    setSearchParams(next)
  }

  const setCurrentPage = (page: number) => {
    const safePage = Math.max(1, page)
    const next = new URLSearchParams(searchParams)
    if (safePage === 1) next.delete('page')
    else next.set('page', safePage.toString())
    setSearchParams(next)
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

      {/* Фильтры: категория, принадлежность, отдел (для директора/зама) */}
      <div className="flex flex-wrap items-center gap-4">
        {categories && categories.length > 0 && (
          <>
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
          </>
        )}
        <label className="text-sm font-medium">Принадлежность:</label>
        <Select
          value={selectedScope}
          onChange={(e) => handleScopeChange((e.target.value || 'all') as ScopeFilter)}
          className="w-40"
        >
          <option value="all">Все</option>
          <option value="my_department">Мой отдел</option>
        </Select>
        {isDirectorOrDeputy && departments && departments.length > 0 && (
          <>
            <label className="text-sm font-medium">Отдел:</label>
            <Select
              value={selectedDepartmentId}
              onChange={(e) => handleDepartmentChange(e.target.value || '')}
              className="w-56"
            >
              <option value="">Все</option>
              {departments.map((dept: { id: number; name: string }) => (
                <option key={dept.id} value={dept.id}>
                  {dept.name}
                </option>
              ))}
            </Select>
          </>
        )}
      </div>

      {totalCount > 0 && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Показано {cards.length} из {totalCount}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(currentPage - 1)}
              disabled={!hasPrevious}
              className="h-8 px-2"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="text-sm text-muted-foreground whitespace-nowrap">
              Страница {currentPage} из {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(currentPage + 1)}
              disabled={!hasNext}
              className="h-8 px-2"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {cards.length > 0 ? (
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

