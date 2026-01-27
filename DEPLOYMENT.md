# Инструкция по развертыванию системы уведомлений на сервере

## Обзор изменений

Добавлена система реальных уведомлений с использованием:
- **WebSocket** (Django Channels) для мгновенных уведомлений в браузере
- **Firebase Cloud Messaging (FCM)** для push-уведомлений на мобильных устройствах
- **Системные браузерные уведомления** (Web Notification API)

## Предварительные требования

1. **Python 3.8+**
2. **Redis** (для Channel Layer в продакшене)
3. **Firebase проект** с сервисным аккаунтом
4. **Nginx** (для проксирования WebSocket)
5. **Daphne или Uvicorn** (ASGI сервер)

---

## Шаг 1: Обновление кода на сервере

```bash
# Перейти в директорию проекта
cd /path/to/taskmanager

# Получить последние изменения из Git
git pull origin main  # или ваша ветка

# Проверить, что все файлы обновлены
git status
```

---

## Шаг 2: Установка зависимостей

### 2.1. Обновление Python зависимостей

```bash
# Активировать виртуальное окружение (если используется)
source venv/bin/activate  # или source source/bin/activate

# Установить/обновить зависимости
pip install -r requirements.txt

# Убедиться, что установлены:
# - channels==4.0.0
# - channels-redis==4.2.0
# - firebase-admin==6.5.0
```

### 2.2. Установка Redis (если еще не установлен)

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install redis-server

# CentOS/RHEL
sudo yum install redis

# Запустить Redis
sudo systemctl start redis
sudo systemctl enable redis

# Проверить статус
sudo systemctl status redis

# Проверить подключение
redis-cli ping
# Должно вернуть: PONG
```

---

## Шаг 3: Настройка Firebase

### 3.1. Получение сервисного аккаунта Firebase

1. Перейти в [Firebase Console](https://console.firebase.google.com/)
2. Выбрать ваш проект
3. Перейти в **Project Settings** → **Service Accounts**
4. Нажать **Generate New Private Key**
5. Скачать JSON файл

### 3.2. Загрузка файла на сервер

```bash
# Скопировать файл в корень проекта
# Файл должен называться: service_account.json
scp service_account.json user@server:/path/to/taskmanager/

# Установить правильные права доступа
chmod 600 /path/to/taskmanager/service_account.json

# Проверить, что файл на месте
ls -la /path/to/taskmanager/service_account.json
```

### 3.3. Проверка пути в settings.py

Убедитесь, что в `taskmanager/settings.py` указан правильный путь:

```python
FIREBASE_SERVICE_ACCOUNT_FILE = BASE_DIR / "service_account.json"
```

---

## Шаг 4: Настройка Django Settings

### 4.1. Проверка настроек Channel Layers

В `taskmanager/settings.py` должна быть следующая конфигурация:

```python
# Для продакшена (DEBUG = False)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
```

**Важно:** Убедитесь, что `DEBUG = False` в продакшене!

### 4.2. Проверка ASGI приложения

В `taskmanager/asgi.py` должна быть правильная конфигурация:

```python
from tasks.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
```

---

## Шаг 5: Применение миграций базы данных

```bash
# Применить миграции (если есть новые)
python manage.py migrate

# Проверить статус миграций
python manage.py showmigrations
```

---

## Шаг 6: Сборка фронтенда

```bash
# Перейти в директорию фронтенда
cd frontend

# Установить зависимости (если нужно)
npm install

# Собрать продакшн версию
npm run build

# Вернуться в корень проекта
cd ..
```

---

## Шаг 7: Настройка Nginx для WebSocket

### 7.1. Конфигурация Nginx

Добавьте в конфигурацию Nginx для вашего сайта:

```nginx
server {
    listen 80;
    server_name taskmanager.ziyatker.org;

    # Обычные HTTP запросы
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket для уведомлений
    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Таймауты для WebSocket
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    # Статические файлы
    location /static/ {
        alias /path/to/taskmanager/staticfiles/;
    }

    # Медиа файлы
    location /media/ {
        alias /path/to/taskmanager/media/;
    }
}
```

### 7.2. Перезагрузка Nginx

```bash
# Проверить конфигурацию
sudo nginx -t

# Перезагрузить Nginx
sudo systemctl reload nginx
```

---

## Шаг 8: Запуск ASGI сервера

### 8.1. Использование Daphne (рекомендуется)

```bash
# Установить Daphne (если еще не установлен)
pip install daphne

# Запустить Daphne
daphne -b 127.0.0.1 -p 8001 taskmanager.asgi:application
```

### 8.2. Использование Uvicorn

```bash
# Установить Uvicorn (если еще не установлен)
pip install uvicorn

# Запустить Uvicorn
uvicorn taskmanager.asgi:application --host 127.0.0.1 --port 8001
```

### 8.3. Запуск через systemd (рекомендуется для продакшена)

Создайте файл `/etc/systemd/system/taskmanager.service`:

```ini
[Unit]
Description=TaskManager Django ASGI Application
After=network.target redis.service

[Service]
Type=simple
User=www-data  # или ваш пользователь
WorkingDirectory=/path/to/taskmanager
Environment="PATH=/path/to/taskmanager/venv/bin"
ExecStart=/path/to/taskmanager/venv/bin/daphne -b 127.0.0.1 -p 8001 taskmanager.asgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Затем:

```bash
# Перезагрузить systemd
sudo systemctl daemon-reload

# Запустить сервис
sudo systemctl start taskmanager

# Включить автозапуск
sudo systemctl enable taskmanager

# Проверить статус
sudo systemctl status taskmanager

# Просмотр логов
sudo journalctl -u taskmanager -f
```

---

## Шаг 9: Проверка работы

### 9.1. Проверка Redis

```bash
redis-cli ping
# Должно вернуть: PONG
```

### 9.2. Проверка Django

```bash
# Проверить, что Django запускается
python manage.py check

# Проверить WebSocket маршруты
python manage.py show_urls | grep ws
```

### 9.3. Проверка WebSocket соединения

Откройте браузерную консоль и проверьте:

```javascript
// В консоли браузера
const ws = new WebSocket('ws://taskmanager.ziyatker.org/ws/notifications/');
ws.onopen = () => console.log('WebSocket connected');
ws.onerror = (e) => console.error('WebSocket error:', e);
```

### 9.4. Проверка Firebase

```bash
# Запустить Django shell
python manage.py shell

# В shell выполнить:
from tasks.notifications import send_task_notification
from django.contrib.auth.models import User

user = User.objects.first()
if user:
    send_task_notification(
        user=user,
        title="Тест",
        body="Тестовое уведомление",
        task_id=1,
        notification_type='task_update'
    )
```

---

## Шаг 10: Сборка статических файлов

```bash
# Собрать статические файлы
python manage.py collectstatic --noinput

# Проверить, что файлы собраны
ls -la staticfiles/
```

---

## Шаг 11: Обновление фронтенда

Если фронтенд развернут отдельно:

```bash
cd frontend
npm run build

# Скопировать собранные файлы в нужное место
# или настроить автоматическую сборку на сервере
```

---

## Возможные проблемы и решения

### Проблема 1: WebSocket не подключается

**Решение:**
- Проверьте, что Redis запущен: `redis-cli ping`
- Проверьте, что Daphne/Uvicorn запущен на порту 8001
- Проверьте логи Nginx: `sudo tail -f /var/log/nginx/error.log`
- Проверьте логи Django: `sudo journalctl -u taskmanager -f`

### Проблема 2: Firebase не инициализируется

**Решение:**
- Проверьте путь к `service_account.json`
- Проверьте права доступа к файлу: `chmod 600 service_account.json`
- Проверьте логи Django на наличие ошибок Firebase

### Проблема 3: Уведомления не отправляются

**Решение:**
- Проверьте логи Django: `sudo journalctl -u taskmanager -f`
- Проверьте, что пользователь авторизован при подключении WebSocket
- Проверьте, что Channel Layer настроен правильно

### Проблема 4: Redis connection refused

**Решение:**
```bash
# Проверить статус Redis
sudo systemctl status redis

# Перезапустить Redis
sudo systemctl restart redis

# Проверить конфигурацию в settings.py
# Убедитесь, что hosts указан правильно: [("127.0.0.1", 6379)]
```

---

## Чеклист развертывания

- [ ] Код обновлен из Git
- [ ] Зависимости установлены (channels, channels-redis, firebase-admin)
- [ ] Redis установлен и запущен
- [ ] Firebase service_account.json загружен на сервер
- [ ] DEBUG = False в settings.py
- [ ] CHANNEL_LAYERS настроен на Redis
- [ ] Миграции применены
- [ ] Фронтенд собран (npm run build)
- [ ] Статические файлы собраны (collectstatic)
- [ ] Nginx настроен для WebSocket
- [ ] Daphne/Uvicorn запущен
- [ ] Systemd сервис создан и запущен (опционально)
- [ ] WebSocket соединение работает
- [ ] Уведомления отправляются

---

## Дополнительные рекомендации

1. **Мониторинг:** Настройте мониторинг Redis и Django процессов
2. **Логирование:** Настройте ротацию логов для Django и Nginx
3. **Безопасность:** Убедитесь, что `service_account.json` не доступен через веб-сервер
4. **Производительность:** Рассмотрите использование Redis Sentinel для высокой доступности
5. **Резервное копирование:** Регулярно делайте бэкап базы данных

---

## Контакты и поддержка

При возникновении проблем проверьте:
1. Логи Django: `sudo journalctl -u taskmanager -f`
2. Логи Nginx: `sudo tail -f /var/log/nginx/error.log`
3. Логи Redis: `sudo tail -f /var/log/redis/redis-server.log`
