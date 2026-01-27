"""
Django settings for taskmanager project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Загружаем переменные окружения (.env) для OpenAI
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-9^7%%f7ypwxngwb#b@bfr78!08d$rst#uve-4gtq54an)8+if7'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '85.202.192.108', 'taskmanager.ziyatker.org']

CSRF_TRUSTED_ORIGINS = [
    "http://85.202.192.108:8001",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://taskmanager.ziyatker.org",
    "http://taskmanager.ziyatker.org",
    "http://localhost:8002",  # 🔥 НОВОЕ: Добавлен порт 8002
    "http://127.0.0.1:8002",
]

# Добавьте путь к собранному фронтенду (Настройка друга)
FRONTEND_BUILD_DIR = BASE_DIR / 'frontend' / 'dist'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Сторонние библиотеки
    'rest_framework',
    'rest_framework.authtoken',  # 🔥 ТВОЕ: Нужно для мобильного входа
    'corsheaders',
    'channels',                  # ДРУГА: Веб-сокеты
    'widget_tweaks',             # ДРУГА: Для форм
    
    # Наши приложения
    'tasks.apps.TasksConfig',
    'assistant',      
    'smartapi',           # 🔥 ТВОЕ: Ассистент
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # ДРУГА: Статика
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tasks.middleware.delegation_freeze.DelegationFreezeMiddleware', # ДРУГА: Делегирование
]

ROOT_URLCONF = 'taskmanager.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # 'tasks.context_processors.unread_notifications', # ⚠️ ЗАКОММЕНТИРОВАНО: Мобилка использует API, а веб отключен.
            ],
        },
    },
]

WSGI_APPLICATION = 'taskmanager.wsgi.application'
# ДРУГА: Каналы для веб-сокетов
ASGI_APPLICATION = 'taskmanager.asgi.application'

# 🔥 ВАЖНО: Настройки каналов (Channels) для WebSocket уведомлений
# Для разработки используем InMemoryChannelLayer
# Для продакшена рекомендуется использовать Redis
if DEBUG:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
else:
    # Для продакшена используем Redis (нужно установить channels-redis)
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [("127.0.0.1", 6379)],  # Адрес Redis сервера
            },
        },
    }

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = "Asia/Almaty"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static", FRONTEND_BUILD_DIR]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Редиректы
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Медиа
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 🔥 ТВОЕ: Настройки Firebase
FIREBASE_SERVICE_ACCOUNT_FILE = BASE_DIR / "service_account.json"

# 🔥 ТВОЕ: API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# REST Framework (ГИБРИДНАЯ НАСТРОЙКА)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',   # 🔥 Для мобилки
        'rest_framework.authentication.SessionAuthentication', # 🌍 Для сайта
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
# Разрешаем вообще всё для удобства разработки мобилки
CORS_ALLOW_ALL_ORIGINS = True 
CORS_ALLOW_CREDENTIALS = True