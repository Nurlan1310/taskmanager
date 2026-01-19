import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { UserCheck} from 'lucide-react'
import { formatDateInAstanaTime } from '@/lib/dateUtils'

interface Delegation {
  id: number
  delegate_to: {
    id: number
    user: {
      first_name: string
      last_name: string
    }
    position?: string
  }
  delegate_until?: string
  is_active: boolean
}

export default function Delegation() {
  const { data: delegations, isLoading } = useQuery<Delegation[]>({
    queryKey: ['delegations'],
    queryFn: async () => {
      // TODO: создать API endpoint для делегирования
      return []
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Замещение</h1>
        <p className="text-muted-foreground mt-2">
          Управление временным замещением сотрудников
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Активные замещения</CardTitle>
        </CardHeader>
        <CardContent>
          {delegations && delegations.length > 0 ? (
            <div className="space-y-4">
              {delegations.map((delegation) => (
                <div
                  key={delegation.id}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="flex items-center gap-4">
                    <UserCheck className="w-8 h-8 text-primary" />
                    <div>
                      <p className="font-semibold">
                        {`${delegation.delegate_to.user.first_name} ${delegation.delegate_to.user.last_name}`}
                      </p>
                      {delegation.delegate_to.position && (
                        <p className="text-sm text-muted-foreground">
                          {delegation.delegate_to.position}
                        </p>
                      )}
                      {delegation.delegate_until && (
                        <p className="text-sm text-muted-foreground">
                          До: {formatDateInAstanaTime(delegation.delegate_until)}
                        </p>
                      )}
                    </div>
                  </div>
                  <Badge variant={delegation.is_active ? 'default' : 'secondary'}>
                    {delegation.is_active ? 'Активно' : 'Неактивно'}
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-muted-foreground">Нет активных замещений</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
