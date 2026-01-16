import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Search, Bell, MessageSquare } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useSearchStore } from '@/store/searchStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export default function Header() {
  const { user } = useAuthStore()
  const { query, setQuery } = useSearchStore()
  const navigate = useNavigate()
  const [searchValue, setSearchValue] = useState(query)

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setQuery(searchValue)
    if (searchValue.trim()) {
      navigate(`/tasks?search=${encodeURIComponent(searchValue)}`)
    }
  }

  const getInitials = () => {
    if (user?.first_name && user?.last_name) {
      return `${user.first_name[0]}${user.last_name[0]}`.toUpperCase()
    }
    return user?.username[0].toUpperCase() || 'U'
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between px-6">
        {/* Search */}
        <div className="flex-1 max-w-md">
          <form onSubmit={handleSearch} className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Поиск задач..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              className="w-full pl-10 pr-4"
            />
          </form>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon">
            <MessageSquare className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon">
            <Bell className="w-5 h-5" />
          </Button>

          {/* User */}
          <Link
            to="/profile"
            className="flex items-center gap-3 hover:opacity-80 transition-opacity cursor-pointer"
          >
            <div className="text-right hidden md:block">
              <div className="text-sm font-medium">
                {user?.first_name && user?.last_name
                  ? `${user.first_name} ${user.last_name}`
                  : user?.username}
              </div>
              {user?.employee?.position && (
                <div className="text-xs text-muted-foreground">
                  {user.employee.position}
                </div>
              )}
            </div>
            {user?.employee?.photo_url ? (
              <img
                src={user.employee.photo_url}
                alt="Фото профиля"
                className="w-10 h-10 rounded-full object-cover border-2 border-primary"
              />
            ) : (
              <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white font-semibold">
                {getInitials()}
              </div>
            )}
          </Link>
        </div>
      </div>
    </header>
  )
}

