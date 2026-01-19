import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { User, Camera, Save, Lock } from 'lucide-react'
// Простая функция для показа уведомлений
const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  // Можно заменить на более продвинутую систему уведомлений
  if (type === 'success') {
    alert(message)
  } else {
    alert(`Ошибка: ${message}`)
  }
}

export default function Profile() {
  const { user, checkAuth } = useAuthStore()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const [formData, setFormData] = useState({
    firstname: user?.employee?.firstname || '',
    lastname: user?.employee?.lastname || '',
    middlename: user?.employee?.middlename || '',
    email: user?.email || '',
  })
  
  const [passwordData, setPasswordData] = useState({
    old_password: '',
    new_password: '',
    confirm_password: '',
  })
  
  const [photoPreview, setPhotoPreview] = useState<string | null>(
    user?.employee?.photo_url || null
  )
  const [selectedPhoto, setSelectedPhoto] = useState<File | null>(null)

  // Загружаем актуальные данные профиля
  const { data: profileData } = useQuery({
    queryKey: ['profile'],
    queryFn: async () => {
      const response = await api.get('/auth/me/')
      return response.data
    },
  })
  useEffect(() => {
    if (profileData) {
      setFormData({
        firstname: profileData.employee?.firstname || '',
        lastname: profileData.employee?.lastname || '',
        middlename: profileData.employee?.middlename || '',
        email: profileData.email || '',
      })
      setPhotoPreview(profileData.employee?.photo_url || null)
    }
  }, [profileData])
  
  const updateProfileMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      return api.put('/auth/profile/', data)
    },
    onSuccess: async () => {
      await checkAuth()
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      showToast('Профиль успешно обновлен', 'success')
    },
    onError: (error: any) => {
      showToast(error.response?.data?.error || 'Ошибка при обновлении профиля', 'error')
    },
  })

  const changePasswordMutation = useMutation({
    mutationFn: async (data: typeof passwordData) => {
      return api.post('/auth/change-password/', data)
    },
    onSuccess: () => {
      setPasswordData({
        old_password: '',
        new_password: '',
        confirm_password: '',
      })
      showToast('Пароль успешно изменен', 'success')
    },
    onError: (error: any) => {
      showToast(error.response?.data?.error || 'Ошибка при изменении пароля', 'error')
    },
  })

  const uploadPhotoMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('photo', file)
      return api.post('/auth/upload-photo/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
    },
    onSuccess: async () => {
      await checkAuth()
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      setSelectedPhoto(null)
      showToast('Фото профиля успешно загружено', 'success')
    },
    onError: (error: any) => {
      showToast(error.response?.data?.error || 'Ошибка при загрузке фото', 'error')
    },
  })

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedPhoto(file)
      const reader = new FileReader()
      reader.onloadend = () => {
        setPhotoPreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleUploadPhoto = () => {
    if (selectedPhoto) {
      uploadPhotoMutation.mutate(selectedPhoto)
    }
  }

  const handleProfileSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateProfileMutation.mutate(formData)
  }

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    changePasswordMutation.mutate(passwordData)
  }

  const getInitials = () => {
    if (formData.middlename && formData.firstname) {
      return `${formData.middlename[0]}${formData.firstname[0]}`.toUpperCase()
    }
    return user?.username[0].toUpperCase() || 'U'
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">Профиль</h1>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Левая колонка - Фото профиля */}
        <Card>
          <CardHeader>
            <CardTitle>Фото профиля</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col items-center gap-4">
              <div className="relative">
                {photoPreview ? (
                  <img
                    src={photoPreview}
                    alt="Фото профиля"
                    className="w-32 h-32 rounded-full object-cover border-4 border-primary"
                  />
                ) : (
                  <div className="w-32 h-32 rounded-full bg-primary flex items-center justify-center text-white text-4xl font-semibold border-4 border-primary">
                    {getInitials()}
                  </div>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handlePhotoChange}
                className="hidden"
              />
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Camera className="w-4 h-4 mr-2" />
                  Выбрать фото
                </Button>
                {selectedPhoto && (
                  <Button
                    type="button"
                    onClick={handleUploadPhoto}
                    disabled={uploadPhotoMutation.isPending}
                  >
                    {uploadPhotoMutation.isPending ? 'Загрузка...' : 'Загрузить'}
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Правая колонка - Основная информация */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="w-5 h-5" />
              Основная информация
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleProfileSubmit} className="space-y-4">
              <div>
                <Label htmlFor="username">Логин</Label>
                <Input
                  id="username"
                  value={user?.username || ''}
                  disabled
                  className="bg-muted"
                />
              </div>
              <div>
                <Label htmlFor="middlename">Фамилия</Label>
                <Input
                  id="middlename"
                  value={formData.middlename}
                  onChange={(e) =>
                    setFormData({ ...formData, middlename: e.target.value })
                  }
                />
              </div>
              <div>
                <Label htmlFor="firstname">Имя</Label>
                <Input
                  id="firstname"
                  value={formData.firstname}
                  onChange={(e) =>
                    setFormData({ ...formData, firstname: e.target.value })
                  }
                />
              </div>
              <div>
                <Label htmlFor="lastname">Отчество</Label>
                <Input
                  id="lastname"
                  value={formData.lastname}
                  onChange={(e) =>
                    setFormData({ ...formData, lastname: e.target.value })
                  }
                />
              </div>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  required
                />
              </div>
              <Button
                type="submit"
                disabled={updateProfileMutation.isPending}
                className="w-full"
              >
                <Save className="w-4 h-4 mr-2" />
                {updateProfileMutation.isPending ? 'Сохранение...' : 'Сохранить изменения'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      {/* Изменение пароля */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="w-5 h-5" />
            Изменение пароля
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div>
              <Label htmlFor="old_password">Текущий пароль</Label>
              <Input
                id="old_password"
                type="password"
                value={passwordData.old_password}
                onChange={(e) =>
                  setPasswordData({ ...passwordData, old_password: e.target.value })
                }
                required
              />
            </div>
            <div>
              <Label htmlFor="new_password">Новый пароль</Label>
              <Input
                id="new_password"
                type="password"
                value={passwordData.new_password}
                onChange={(e) =>
                  setPasswordData({ ...passwordData, new_password: e.target.value })
                }
                required
              />
            </div>
            <div>
              <Label htmlFor="confirm_password">Подтвердите новый пароль</Label>
              <Input
                id="confirm_password"
                type="password"
                value={passwordData.confirm_password}
                onChange={(e) =>
                  setPasswordData({ ...passwordData, confirm_password: e.target.value })
                }
                required
              />
            </div>
            <Button
              type="submit"
              disabled={changePasswordMutation.isPending}
              className="w-full"
            >
              {changePasswordMutation.isPending ? 'Изменение...' : 'Изменить пароль'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

