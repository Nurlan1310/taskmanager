from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.static import serve

urlpatterns = [
    # 1. Админка (общая)
    path('admin/', admin.site.urls),

    # 2. Аккаунты (вход/выход для админки и прочего)
    path('accounts/', include('django.contrib.auth.urls')),
    
    # ==========================================================
    # 🔥 API
    # ==========================================================
    
    # А) API ДРУГА (для его веб-сайта)
    # Оставляем, чтобы его сайт не сломался.
    path('api/', include('tasks.api_urls')),

    # Б) ТВОЙ API (для мобильного приложения)
    # Мы подключаем файл tasks.urls, где прописаны твои my-tasks, notifications и т.д.
    # Так как пути разные (my-tasks vs tasks), они не будут конфликтовать.
    path('api/', include('tasks.urls')),


    # ==========================================================
    # ⛔️ ФРОНТЕНД ДРУГА (НЕ ТРОГАЕМ)
    # ==========================================================
    
    # Раздача статики фронтенда (JS/CSS из папки assets)
    re_path(r'^assets/.*$', serve, {'document_root': settings.BASE_DIR / 'frontend/dist/assets'}),
    
    # React Router (перехватывает все остальные запросы и отдает index.html)
    # Это обеспечивает работу его дизайна сайта.
    re_path(r'^(?!api|admin|accounts|static|media|assets).*$', 
            TemplateView.as_view(template_name='index.html')),
]

# Раздача медиа-файлов (аватарки, файлы задач)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)