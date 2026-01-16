# Инструкция по установке и запуску

## Предварительные требования

- Python 3.8+
- Node.js 18+
- npm или yarn

## Установка Backend

1. Создайте виртуальное окружение (рекомендуется):
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Примените миграции:
```bash
python manage.py migrate
```

4. Создайте суперпользователя (опционально):
```bash
python manage.py createsuperuser
```

5. Запустите сервер разработки:
```bash
python manage.py runserver 8001
```

Backend будет доступен по адресу `http://localhost:8001`

## Установка Frontend

1. Перейдите в папку frontend:
```bash
cd frontend
```

2. Установите зависимости:
```bash
npm install
```

3. Запустите dev-сервер:
```bash
npm run dev
```

Frontend будет доступен по адресу `http://localhost:5173`

## Первый запуск

1. Запустите backend сервер (порт 8001)
2. Запустите frontend сервер (порт 5173)
3. Откройте браузер и перейдите на `http://localhost:5173`
4. Войдите используя учетные данные суперпользователя или создайте нового пользователя через Django admin

## Структура проекта

```
taskmanager/
├── frontend/          # React приложение
│   ├── src/
│   │   ├── components/   # React компоненты
│   │   ├── pages/         # Страницы
│   │   ├── lib/           # Утилиты
│   │   └── store/         # Zustand stores
│   └── package.json
│
├── tasks/            # Django приложение
│   ├── models.py
│   ├── serializers.py
│   ├── api_views.py
│   └── api_urls.py
│
└── taskmanager/     # Настройки Django
    ├── settings.py
    └── urls.py
```

## API Endpoints

Все API endpoints доступны по адресу `/api/`:

- `POST /api/auth/login/` - Вход
- `POST /api/auth/logout/` - Выход  
- `GET /api/auth/me/` - Текущий пользователь
- `GET /api/dashboard/` - Статистика дашборда
- `GET /api/tasks/` - Список задач
- `GET /api/cards/` - Список мероприятий
- `GET /api/employees/` - Список сотрудников

## Разработка

### Добавление новых компонентов

Компоненты UI находятся в `frontend/src/components/ui/` и следуют стилю shadcn/ui.

### Добавление новых API endpoints

1. Добавьте сериализатор в `tasks/serializers.py`
2. Создайте ViewSet в `tasks/api_views.py`
3. Зарегистрируйте в `tasks/api_urls.py`

## Troubleshooting

### CORS ошибки
Убедитесь, что `CORS_ALLOWED_ORIGINS` в `settings.py` включает `http://localhost:5173`

### CSRF ошибки
Убедитесь, что axios настроен для отправки CSRF токена (уже настроено в `frontend/src/lib/api.ts`)

### Проблемы с зависимостями
Удалите `node_modules` и `package-lock.json`, затем выполните `npm install` заново

