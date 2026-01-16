# TaskManager - Современный менеджер задач

Профессиональная система управления задачами с современным стеком технологий.

## Технологический стек

### Backend
- **Django 4.2** - веб-фреймворк
- **Django REST Framework** - API
- **Django Channels** - WebSocket поддержка (для будущих real-time функций)
- **SQLite** - база данных (можно заменить на PostgreSQL)

### Frontend
- **React 18** - UI библиотека
- **TypeScript** - типизация
- **Vite** - сборщик и dev-сервер
- **Tailwind CSS** - стилизация
- **shadcn/ui** - компоненты UI
- **TanStack Query** - управление серверным состоянием
- **Zustand** - управление клиентским состоянием
- **React Router** - маршрутизация
- **dnd-kit** - drag-and-drop
- **FullCalendar** - календарь

## Установка и запуск

### Backend

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Примените миграции:
```bash
python manage.py migrate
```

3. Создайте суперпользователя (опционально):
```bash
python manage.py createsuperuser
```

4. Запустите сервер разработки:
```bash
python manage.py runserver 8001
```

### Frontend

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

Приложение будет доступно по адресу `http://localhost:5173`

## Структура проекта

```
taskmanager/
├── frontend/              # React приложение
│   ├── src/
│   │   ├── components/   # React компоненты
│   │   │   ├── ui/       # UI компоненты (shadcn/ui)
│   │   │   └── layout/   # Layout компоненты
│   │   ├── pages/        # Страницы приложения
│   │   ├── lib/          # Утилиты и API клиент
│   │   ├── store/        # Zustand stores
│   │   └── App.tsx       # Главный компонент
│   └── package.json
│
├── tasks/                # Django приложение
│   ├── models.py         # Модели данных
│   ├── serializers.py    # DRF сериализаторы
│   ├── api_views.py      # API представления
│   └── api_urls.py       # API маршруты
│
└── taskmanager/          # Настройки Django
    ├── settings.py
    └── urls.py
```

## API Endpoints

### Аутентификация
- `POST /api/auth/login/` - Вход
- `POST /api/auth/logout/` - Выход
- `GET /api/auth/me/` - Текущий пользователь

### Дашборд
- `GET /api/dashboard/` - Статистика дашборда

### Задачи
- `GET /api/tasks/` - Список задач
- `POST /api/tasks/` - Создать задачу
- `GET /api/tasks/{id}/` - Детали задачи
- `PUT /api/tasks/{id}/` - Обновить задачу
- `DELETE /api/tasks/{id}/` - Удалить задачу

### Мероприятия
- `GET /api/cards/` - Список мероприятий
- `POST /api/cards/` - Создать мероприятие
- `GET /api/cards/{id}/` - Детали мероприятия
- `PUT /api/cards/{id}/` - Обновить мероприятие
- `DELETE /api/cards/{id}/` - Удалить мероприятие

### Сотрудники
- `GET /api/employees/` - Список сотрудников

## Фильтрация задач

- `?status=new` - Новые задачи
- `?status=in_progress` - В работе
- `?status=done` - Выполненные
- `?task_type=approval` - На согласовании
- `?card={id}` - Задачи конкретного мероприятия

## Разработка

### Добавление новых компонентов UI

Компоненты shadcn/ui можно добавлять через CLI (если установлен) или вручную в `frontend/src/components/ui/`.

### Добавление новых API endpoints

1. Добавьте сериализатор в `tasks/serializers.py`
2. Создайте ViewSet в `tasks/api_views.py`
3. Зарегистрируйте в `tasks/api_urls.py`

## Следующие шаги

- [ ] Реализовать страницы Tasks, Cards с полным функционалом
- [ ] Добавить drag-and-drop для задач (dnd-kit)
- [ ] Интегрировать FullCalendar
- [ ] Добавить real-time обновления через WebSocket (Channels)
- [ ] Добавить фильтры и поиск
- [ ] Добавить уведомления
- [ ] Оптимизировать производительность

## Лицензия

MIT

