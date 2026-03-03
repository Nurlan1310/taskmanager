from rest_framework import viewsets, status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q, Count, Max
from django.db.models.expressions import RawSQL
from django.db import connection
from django.utils import timezone
from datetime import timedelta, datetime
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import (
    Task, EventCard, Employee, Category, Department, CardApproverOrder, TaskHistory, Notification,
    TaskApprovalChain, TaskReviewChain, TaskRedirectChain
)
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import FileResponse
from urllib.parse import quote
import mimetypes
import os
from .serializers import (
    TaskSerializer, EventCardSerializer, EventCardDetailSerializer,
    EmployeeSerializer, UserSerializer, CategorySerializer, DepartmentSerializer, NotificationSerializer
)


class TaskPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 100


class CardPagination(PageNumberPagination):
    page_size = 24


@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf_view(request):
    """Вернуть CSRF cookie для SPA"""
    return Response({'detail': 'CSRF cookie set'})


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password required', 'error_type': 'missing_fields'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверяем, существует ли пользователь с таким логином
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response(
            {'error': 'Пользователь с таким логином не существует', 'error_type': 'user_not_found'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Если пользователь существует, проверяем пароль
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        serializer = UserSerializer(user)
        if hasattr(user, 'employee'):
            employee_data = EmployeeSerializer(user.employee).data
            serializer_data = serializer.data
            serializer_data['employee'] = employee_data
            return Response(serializer_data)
        return Response(serializer.data)
    else:
        return Response(
            {'error': 'Неверный пароль', 'error_type': 'invalid_password'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    try:
        employee = request.user.employee
        employee_data = EmployeeSerializer(employee).data if employee else None
        # Добавляем URL фото профиля, если оно есть
        if employee and employee.photo:
            employee_data['photo_url'] = request.build_absolute_uri(employee.photo.url)
        elif employee:
            employee_data['photo_url'] = None
        return Response({
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'employee': employee_data
        })
    except Employee.DoesNotExist:
        return Response({
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'employee': None
        })


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile_view(request):
    """Обновление профиля пользователя"""
    user = request.user
    data = request.data
    
    # Обновляем email пользователя
    if 'email' in data:
        user.email = data['email']
        user.save()
    
    # Обновляем поля Employee (ФИО)
    try:
        employee = user.employee
        if 'firstname' in data:
            employee.firstname = data['firstname']
        if 'lastname' in data:
            employee.lastname = data['lastname']
        if 'middlename' in data:
            employee.middlename = data['middlename']
        employee.save()
        
        employee_data = EmployeeSerializer(employee).data
        if employee.photo:
            employee_data['photo_url'] = request.build_absolute_uri(employee.photo.url)
        else:
            employee_data['photo_url'] = None
    except Employee.DoesNotExist:
        employee_data = None
    
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'employee': employee_data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """Изменение пароля пользователя"""
    user = request.user
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')
    
    if not old_password or not new_password or not confirm_password:
        return Response(
            {'error': 'Все поля обязательны для заполнения'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if new_password != confirm_password:
        return Response(
            {'error': 'Новый пароль и подтверждение не совпадают'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not user.check_password(old_password):
        return Response(
            {'error': 'Неверный текущий пароль'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user.set_password(new_password)
    user.save()
    
    return Response({'message': 'Пароль успешно изменен'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_profile_photo_view(request):
    """Загрузка фото профиля"""
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return Response(
            {'error': 'У пользователя нет связанного сотрудника'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    photo = request.FILES.get('photo')
    if not photo:
        return Response(
            {'error': 'Фото не предоставлено'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Удаляем старое фото, если оно есть
    if employee.photo:
        employee.photo.delete()
    
    employee.photo = photo
    employee.save()
    
    employee_data = EmployeeSerializer(employee).data
    employee_data['photo_url'] = request.build_absolute_uri(employee.photo.url)
    
    return Response({
        'message': 'Фото профиля успешно загружено',
        'employee': employee_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_view(request):
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return Response(
            {'error': 'Employee profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    effective_employee = employee.get_effective_employee()
    now = timezone.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)
    end_of_week = today + timedelta(days=7)
    
    # Время начала и конца дня для корректного сравнения DateTimeField
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    tomorrow_start = timezone.make_aware(datetime.combine(tomorrow, datetime.min.time()))
    tomorrow_end = timezone.make_aware(datetime.combine(tomorrow, datetime.max.time()))
    end_of_week_end = timezone.make_aware(datetime.combine(end_of_week, datetime.max.time()))

    # Базовый queryset для задач пользователя (только те, которые поручили)
    # Включаем также задачи типа review, approval и task_approval, которые назначены пользователю
    base_tasks_qs = Task.objects.filter(
        Q(assigned_employee=effective_employee) |
        Q(recipients=effective_employee) |
        Q(task_type='review', assigned_employee=effective_employee) |  # Задачи на проверку
        Q(task_type='approval', assigned_employee=effective_employee) |  # Задачи на согласование плана
        Q(task_type='task_approval', assigned_employee=effective_employee)  # Задачи на согласование создания
    ).exclude(status='done').distinct().select_related(
        'created_by', 'assigned_employee', 'assigned_department', 'card'
    ).prefetch_related('recipients')

    # Статистика - активные карточки, доступные пользователю
    # Определяем доступные карточки (используем ту же логику, что и в EventCardViewSet)
    if effective_employee.role in ("director", "deputy"):
        # Директор и заместитель видят все карточки
        available_cards = EventCard.objects.all()
    else:
        # Карточки с visible=True - видят все
        # Карточки с visible=False - видят только:
        # 1. Ответственный отдел (responsible_department)
        # 2. Смежные отделы (shared_departments)
        access_filter = Q(visible=True)  # Все видят карточки с visible=True
        
        # Для карточек с visible=False - только свой отдел и смежные
        if effective_employee.department:
            hidden_access = (
                Q(visible=False) &
                (Q(responsible_department=effective_employee.department) |
                 Q(shared_departments=effective_employee.department))
            )
            access_filter |= hidden_access
        
        available_cards = EventCard.objects.filter(access_filter).distinct()
    
    # Фильтруем только активные карточки (start_date <= today и (end_date is None или end_date >= today))
    active_cards = available_cards.filter(
        start_date__lte=today
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    ).distinct()
    
    total_cards = active_cards.count()

    total_tasks = base_tasks_qs.count()

    urgent_tasks = base_tasks_qs.filter(
        due_date__lte=now + timedelta(days=3),
        due_date__isnull=False
    ).count()

    approval_tasks = Task.objects.filter(
        assigned_employee=effective_employee,
        task_type__in=['approval', 'review', 'task_approval']
    ).exclude(status='done').count()

    # Просроченные задачи (due_date < сегодня начало дня)
    overdue_tasks = base_tasks_qs.filter(
        due_date__lt=today_start,
        due_date__isnull=False
    ).exclude(task_type__in=['review', 'approval', 'task_approval']).order_by('due_date')

    # Задачи на сегодня (due_date в пределах сегодняшнего дня)
    # Включаем также задачи review, approval и task_approval (даже без due_date)
    today_tasks = base_tasks_qs.filter(
        Q(due_date__gte=today_start, due_date__lte=today_end, due_date__isnull=False) |
        Q(task_type__in=['review', 'approval', 'task_approval'])
    ).exclude(id__in=overdue_tasks.values_list('id', flat=True)).order_by('due_date', '-created_at')

    # Задачи на завтра (due_date в пределах завтрашнего дня)
    tomorrow_tasks = base_tasks_qs.filter(
        due_date__gte=tomorrow_start,
        due_date__lte=tomorrow_end,
        due_date__isnull=False
    ).exclude(task_type__in=['review', 'approval', 'task_approval']).exclude(id__in=today_tasks.values_list('id', flat=True)).order_by('due_date')

    # Остальные задачи (начиная с послезавтра)
    week_tasks = base_tasks_qs.filter(
        due_date__gt=tomorrow_end,
        due_date__isnull=False
    ).exclude(task_type__in=['review', 'approval', 'task_approval']).exclude(id__in=today_tasks.values_list('id', flat=True)).exclude(id__in=tomorrow_tasks.values_list('id', flat=True)).order_by('due_date')

    return Response({
        'total_cards': total_cards,
        'total_tasks': total_tasks,
        'urgent_tasks': urgent_tasks,
        'approval_tasks': approval_tasks,
        'overdue_tasks': TaskSerializer(overdue_tasks, many=True).data,
        'today_tasks': TaskSerializer(today_tasks, many=True).data,
        'tomorrow_tasks': TaskSerializer(tomorrow_tasks, many=True).data,
        'week_tasks': TaskSerializer(week_tasks, many=True).data,
    })


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TaskPagination  # 30 задач на страницу для страницы Задачи

    def get_queryset(self):
        try:
            employee = self.request.user.employee
        except Employee.DoesNotExist:
            return Task.objects.none()

        effective_employee = employee.get_effective_employee()
        
        # Определяем scope фильтрации
        scope = self.request.query_params.get('scope', 'mine')  # mine, department, all
        employee_id = self.request.query_params.get('employee_id')
        
        # Поручения (assignments): задачи, созданные пользователем или перенаправленные им
        if scope == 'assignments':
            # Используем новую модель TaskRedirectChain вместо JSON поля
            queryset = Task.objects.filter(
                Q(created_by=effective_employee) |
                Q(redirect_chain__from_employee=effective_employee)
            ).distinct()
            
            if employee_id:
                try:
                    filter_employee = Employee.objects.get(id=employee_id)
                    # Задачи, где выбранный сотрудник — исполнитель или в цепочке перенаправлений
                    queryset = queryset.filter(
                        Q(assigned_employee=filter_employee) |
                        Q(redirect_chain__from_employee=filter_employee) |
                        Q(redirect_chain__to_employee=filter_employee)
                    ).distinct()
                except (Employee.DoesNotExist, ValueError):
                    queryset = Task.objects.none()
        # Если указан конкретный сотрудник для фильтрации (для scope != assignments)
        elif employee_id:
            try:
                filter_employee = Employee.objects.get(id=employee_id)
                # Проверяем права доступа
                if effective_employee.role in ("director", "deputy"):
                    # Директор и заместитель могут видеть задачи любого сотрудника
                    # Показываем только задачи где сотрудник назначен исполнителем
                    queryset = Task.objects.filter(
                        Q(assigned_employee=filter_employee) |
                        Q(recipients=filter_employee)
                    ).distinct()
                elif effective_employee.role == "head" and effective_employee.department:
                    # Руководитель отдела может видеть задачи сотрудников своего отдела
                    if filter_employee.department == effective_employee.department:
                        queryset = Task.objects.filter(
                            Q(assigned_employee=filter_employee) |
                            Q(recipients=filter_employee)
                        ).distinct()
                    else:
                        return Task.objects.none()
                else:
                    # Обычный сотрудник может видеть только свои задачи
                    if filter_employee == effective_employee:
                        queryset = Task.objects.filter(
                            Q(assigned_employee=effective_employee) |
                            Q(recipients=effective_employee)
                        ).distinct()
                    else:
                        return Task.objects.none()
            except Employee.DoesNotExist:
                return Task.objects.none()
        else:
            # Фильтрация по scope
            if scope == 'all':
                # Все задачи - только для директора и заместителя
                # Показываем все задачи назначенные кому-либо (assigned_employee не null)
                if effective_employee.role in ("director", "deputy"):
                    queryset = Task.objects.filter(
                        Q(assigned_employee__isnull=False) |
                        Q(assigned_department__isnull=False)
                    )
                else:
                    # Для остальных - только свои задачи
                    queryset = Task.objects.filter(
                        Q(assigned_employee=effective_employee) |
                        Q(recipients=effective_employee)
                    ).distinct()
            elif scope == 'department':
                # Задачи отдела - показываем задачи назначенные отделу или сотрудникам отдела
                if effective_employee.department:
                    queryset = Task.objects.filter(
                        Q(assigned_department=effective_employee.department) |
                        Q(assigned_employee__department=effective_employee.department)
                    ).distinct()
                else:
                    queryset = Task.objects.filter(
                        Q(assigned_employee=effective_employee) |
                        Q(recipients=effective_employee)
                    ).distinct()
            else:  # scope == 'mine' (по умолчанию)
                # Мои задачи - только те, которые поручили мне
                queryset = Task.objects.filter(
                    Q(assigned_employee=effective_employee) |
                    Q(recipients=effective_employee)
                ).distinct()
        
        queryset = queryset.select_related(
            'created_by', 'assigned_employee', 'assigned_department', 'card', 'redirected_by'
        ).prefetch_related('recipients', 'history')

        # Фильтры
        status_filter = self.request.query_params.get('status')
        include_done = self.request.query_params.get('include_done', '').lower() == 'true'
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        elif not include_done:
            # По умолчанию исключаем выполненные задачи (для "Активные"); календарь передаёт include_done=true
            queryset = queryset.exclude(status='done')

        task_type = self.request.query_params.get('task_type')
        # Специальная обработка для фильтра "На согласовании" (approval и review)
        approval_review_filter = self.request.query_params.get('approval_review', 'false').lower() == 'true'
        if approval_review_filter:
            queryset = queryset.filter(task_type__in=['approval', 'review'])
        elif task_type:
            queryset = queryset.filter(task_type=task_type)

        card_id = self.request.query_params.get('card')
        if card_id:
            queryset = queryset.filter(card_id=card_id)

        # Поиск
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset.order_by('-created_at')

    def retrieve(self, request, *args, **kwargs):
        """Получение задачи с проверкой доступа"""
        try:
            employee = request.user.employee
        except Employee.DoesNotExist:
            return Response(
                {'error': 'У пользователя нет связанного сотрудника'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        effective_employee = employee.get_effective_employee()
        
        # Получаем задачу напрямую по ID, не используя get_queryset()
        task_id = kwargs.get('pk')
        try:
            task = Task.objects.select_related(
                'created_by', 'assigned_employee', 'assigned_department', 'card', 'redirected_by'
            ).prefetch_related('recipients', 'history').get(id=task_id)
        except Task.DoesNotExist:
            return Response(
                {'error': 'Задача не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Проверяем доступ
        has_access = False
        
        if effective_employee.role in ("director", "deputy"):
            # Директор и заместитель видят все задачи
            has_access = True
        elif effective_employee.role == "head" and effective_employee.department:
            # Руководитель отдела видит:
            # 1. Свои задачи (где он автор или исполнитель)
            # 2. Задачи сотрудников своего отдела
            has_access = (
                task.created_by == effective_employee or
                task.assigned_employee == effective_employee or
                effective_employee in task.recipients.all() or
                (task.assigned_department == effective_employee.department) or
                (task.assigned_employee and task.assigned_employee.department == effective_employee.department)
            )
        else:
            # Обычный сотрудник видит только свои задачи (где он автор или исполнитель)
            has_access = (
                task.created_by == effective_employee or
                task.assigned_employee == effective_employee or
                effective_employee in task.recipients.all()
            )
        
        if not has_access:
            return Response(
                {'error': 'У вас нет доступа к этой задаче'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Если доступ есть, сериализуем и возвращаем задачу
        serializer = self.get_serializer(task)
        return Response(serializer.data)

    def get_object(self):
        """Переопределяем get_object для получения задачи напрямую по ID с проверкой доступа"""
        # Получаем ID задачи из kwargs
        task_id = self.kwargs.get('pk')
        
        try:
            employee = self.request.user.employee
        except Employee.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('У пользователя нет связанного сотрудника')
        
        effective_employee = employee.get_effective_employee()
        
        # Получаем задачу напрямую по ID
        try:
            task = Task.objects.select_related(
                'created_by', 'assigned_employee', 'assigned_department', 'card', 'redirected_by'
            ).prefetch_related('recipients', 'history').get(id=task_id)
        except Task.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Задача не найдена')
        
        # Проверяем доступ (аналогично retrieve)
        has_access = False
        
        if effective_employee.role in ("director", "deputy"):
            has_access = True
        elif effective_employee.role == "head" and effective_employee.department:
            has_access = (
                task.created_by == effective_employee or
                task.assigned_employee == effective_employee or
                effective_employee in task.recipients.all() or
                (task.assigned_department == effective_employee.department) or
                (task.assigned_employee and task.assigned_employee.department == effective_employee.department)
            )
        else:
            has_access = (
                task.created_by == effective_employee or
                task.assigned_employee == effective_employee or
                effective_employee in task.recipients.all()
            )
        
        if not has_access:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('У вас нет доступа к этой задаче')
        
        return task

    def _determine_approvers(self, creator, is_according_to_plan, deputy_id=None):
        """
        Определяет цепочку согласующих для создания задачи.
        
        Логика:
        1. Согласно плана:
           - staff -> head отдела
           - senior/head/deputy/director -> без согласования
        2. Не согласно плана:
           - staff -> head отдела, затем выбранный deputy/director
           - senior/head -> только выбранный deputy/director
           - deputy/director -> без согласования
        
        Returns:
            list: Список Employee объектов - согласующие в порядке согласования
        """
        approvers = []
        creator_role = creator.role
        creator_dept = creator.department
        
        # Определяем руководителя отдела
        head = None
        if creator_dept:
            head = Employee.objects.filter(
                department=creator_dept,
                role='head'
            ).first()
        
        if is_according_to_plan:
            # Согласно плана: только staff нуждается в согласовании head
            if creator_role == 'staff' and head:
                approvers = [head]
        else:
            # Не согласно плана
            # Получаем выбранного заместителя или директора
            deputy_or_director = None
            if deputy_id:
                try:
                    # Может быть либо заместитель, либо директор
                    deputy_or_director = Employee.objects.get(
                        id=deputy_id, 
                        role__in=['deputy', 'director']
                    )
                except Employee.DoesNotExist:
                    pass
            
            if creator_role == 'staff':
                # Обычный сотрудник: head, затем deputy/director
                if head:
                    approvers.append(head)
                if deputy_or_director:
                    approvers.append(deputy_or_director)
            elif creator_role in ['senior', 'head']:
                # Старший сотрудник или руководитель: только deputy/director
                if deputy_or_director:
                    approvers.append(deputy_or_director)
            # deputy и director создают без согласования
        
        return approvers

    def create(self, request, *args, **kwargs):
        """Создание задачи(задач) - если адресатов несколько, создаем отдельную задачу для каждого"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            employee = request.user.employee
        except Employee.DoesNotExist:
            raise serializers.ValidationError({'error': 'У пользователя нет связанного сотрудника'})
        
        # Проверяем активность карточки, если она указана
        card_id = request.data.get('card')
        if card_id:
            try:
                card = EventCard.objects.get(id=card_id)
                today = timezone.now().date()
                
                # Проверяем, активна ли карточка
                is_active = False
                if not card.end_date:
                    is_active = card.start_date <= today
                else:
                    is_active = card.start_date <= today <= card.end_date
                
                if not is_active:
                    if card.end_date and card.end_date < today:
                        raise serializers.ValidationError({
                            'card': 'Нельзя создавать задачи в архивных карточках (срок мероприятия истек).'
                        })
                    else:
                        raise serializers.ValidationError({
                            'card': 'Нельзя создавать задачи в карточках, которые еще не начались.'
                        })
            except EventCard.DoesNotExist:
                raise serializers.ValidationError({'card': 'Указанная карточка не существует.'})
        
        # Получаем recipients из request.data
        # FormData может передавать несколько значений с одним именем как список
        # Используем getlist() для QueryDict (FormData) или get() для обычного dict (JSON)
        if hasattr(request.data, 'getlist'):
            recipients_ids_raw = request.data.getlist('recipients_ids')
        else:
            recipients_ids_raw = request.data.get('recipients_ids', [])
        
        # Преобразуем в список целых чисел
        if not recipients_ids_raw:
            recipients_ids = []
        elif isinstance(recipients_ids_raw, str):
            recipients_ids = [int(recipients_ids_raw)]
        elif isinstance(recipients_ids_raw, list):
            recipients_ids = [int(rid) for rid in recipients_ids_raw if rid and str(rid).strip()]
        else:
            recipients_ids = []
        
        # Получаем параметры согласования
        is_according_to_plan = request.data.get('is_according_to_plan', True)
        if isinstance(is_according_to_plan, str):
            is_according_to_plan = is_according_to_plan.lower() in ('true', '1', 'yes')
        
        deputy_id = request.data.get('creation_deputy_id')
        if deputy_id:
            try:
                deputy_id = int(deputy_id)
            except (ValueError, TypeError):
                deputy_id = None
        
        # Параметры проверки выполнения
        review_self = request.data.get('review_self', True)
        if isinstance(review_self, str):
            review_self = review_self.lower() in ('true', '1', 'yes')
        
        final_reviewer_id = request.data.get('final_reviewer_id')
        if final_reviewer_id:
            try:
                final_reviewer_id = int(final_reviewer_id)
            except (ValueError, TypeError):
                final_reviewer_id = None
        
        # Определяем согласующих
        approvers = self._determine_approvers(employee, is_according_to_plan, deputy_id)
        
        # Получаем файл и Google Drive ссылку для создания вложений
        file = request.FILES.get('file') or request.data.get('file')
        google_drive_link = request.data.get('google_drive_link')
        
        # Если адресатов несколько, создаем отдельную задачу для каждого
        if recipients_ids and len(recipients_ids) > 1:
            from .models import Employee, Task, TaskAttachment
            from django.db import transaction
            from django.core.files.base import ContentFile
            import os
            
            created_tasks = []
            validated_data = serializer.validated_data.copy()
            
            # Удаляем recipients из validated_data, так как будем обрабатывать их отдельно
            validated_data.pop('recipients', None)
            # Удаляем google_drive_link из validated_data, так как будем создавать TaskAttachment
            validated_data.pop('google_drive_link', None)
            
            # Если есть файл, читаем его содержимое один раз для всех задач
            file_content = None
            file_name = None
            if file:
                file_content = file.read()
                file_name = file.name
                file.seek(0)  # Возвращаем указатель в начало для возможного повторного использования
            
            with transaction.atomic():
                for recipient_id in recipients_ids:
                    try:
                        recipient = Employee.objects.get(id=recipient_id)
                    except Employee.DoesNotExist:
                        continue
                    
                    # Создаем задачу для каждого адресата
                    task_data = validated_data.copy()
                    task_data['created_by'] = employee
                    task_data['assigned_employee'] = recipient
                    task_data['is_according_to_plan'] = is_according_to_plan
                    task_data['review_self'] = review_self
                    if final_reviewer_id:
                        try:
                            task_data['final_reviewer'] = Employee.objects.get(id=final_reviewer_id)
                        except Employee.DoesNotExist:
                            task_data['final_reviewer'] = None
                    else:
                        task_data['final_reviewer'] = None
                    
                    # Определяем статус в зависимости от согласующих
                    if approvers:
                        task_data['status'] = 'send_for_approve'
                    else:
                        task_data['status'] = 'new'
                    
                    # Создаем задачу БЕЗ JSON полей (они уже удалены)
                    task = Task.objects.create(**task_data)
                    
                    # Добавляем адресата в M2M
                    task.recipients.add(recipient)
                    
                    # Добавляем согласующих в цепочку (новый способ)
                    if approvers:
                        for order, approver in enumerate(approvers, 1):
                            task.add_to_approval_chain(approver, order=order)
                    
                    # Создаем запись в истории
                    TaskHistory.objects.create(
                        task=task,
                        employee=employee,
                        action='created',
                        comment=f'Задача создана и назначена {recipient.full_name}'
                    )
                    
                    # Если нет согласующих, отправляем уведомление исполнителю
                    if not approvers and task.assigned_employee:
                        try:
                            from .notifications import send_task_notification
                            creator_name = employee.full_name if employee.full_name else employee.user.get_full_name() or employee.user.username
                            send_task_notification(
                                user=task.assigned_employee.user,
                                title="Новая задача",
                                body=f"{creator_name} назначил(-а) вам задачу: {task.title}",
                                task_id=task.id,
                                notification_type='task.created'
                            )
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Ошибка отправки уведомления исполнителю: {e}")
                    
                    # Создаем задачи-согласования, если нужно
                    if approvers:
                        first_approver = approvers[0]
                        approval_task = Task.objects.create(
                            task_type='task_approval',
                            status='new',
                            title=f"Согласование поручения: {task.title}",
                            description=f"Требуется согласование поручения:\n{task.title}",
                            created_by=employee,
                            assigned_employee=first_approver,
                            parent_task=task,
                            relation_type='creation_approval',
                            card=task.card,
                        )
                        TaskHistory.objects.create(
                            task=task,
                            employee=employee,
                            action='sent_for_approve',
                            comment=f'Задача отправлена на согласование создания ({first_approver.full_name})'
                        )
                        TaskHistory.objects.create(
                            task=approval_task,
                            employee=employee,
                            action='created',
                            comment=f'Задача согласования создания создана'
                        )
                        
                        # Отправляем уведомление первому согласующему
                        try:
                            from .notifications import send_task_notification
                            creator_name = employee.full_name if employee.full_name else employee.user.get_full_name() or employee.user.username
                            send_task_notification(
                                user=first_approver.user,
                                title="Требуется согласование",
                                body=f"{creator_name} отправил(-а) поручение «{task.title}» на согласование",
                                task_id=approval_task.id,
                                notification_type='task.approval_required'
                            )
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Ошибка отправки уведомления согласующему: {e}")
                    
                    # Создаем вложения для каждой задачи
                    if file_content and file_name:
                        # Создаем новый файл из сохраненного содержимого для каждой задачи
                        task_file = ContentFile(file_content, name=file_name)
                        TaskAttachment.objects.create(
                            task=task,
                            file=task_file,
                            uploaded_by=employee
                        )
                    if google_drive_link:
                        TaskAttachment.objects.create(
                            task=task,
                            link=google_drive_link,
                            uploaded_by=employee
                        )
                    
                    created_tasks.append(task)
            
            # Возвращаем последнюю созданную задачу (для совместимости с DRF)
            if created_tasks:
                return Response(
                    TaskSerializer(created_tasks[-1]).data,
                    status=status.HTTP_201_CREATED
                )
            else:
                raise serializers.ValidationError({
                    'recipients_ids': 'Не удалось создать задачи для указанных адресатов.'
                })
        else:
            # Если адресат один или не указан, создаем одну задачу через стандартный метод
            self.perform_create(serializer, file=file, google_drive_link=google_drive_link, 
                              is_according_to_plan=is_according_to_plan, deputy_id=deputy_id, approvers=approvers,
                              review_self=review_self, final_reviewer_id=final_reviewer_id)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer, file=None, google_drive_link=None, 
                      is_according_to_plan=True, deputy_id=None, approvers=None,
                      review_self=True, final_reviewer_id=None):
        try:
            employee = self.request.user.employee
        except Employee.DoesNotExist:
            raise serializers.ValidationError({'error': 'У пользователя нет связанного сотрудника'})
        
        # Удаляем google_drive_link из validated_data, так как будем создавать TaskAttachment
        validated_data = serializer.validated_data.copy()
        validated_data.pop('google_drive_link', None)
        
        # Устанавливаем параметры согласования
        if approvers is None:
            approvers = self._determine_approvers(employee, is_according_to_plan, deputy_id)
        
        validated_data['is_according_to_plan'] = is_according_to_plan
        validated_data['review_self'] = review_self
        if final_reviewer_id:
            try:
                validated_data['final_reviewer'] = Employee.objects.get(id=final_reviewer_id)
            except Employee.DoesNotExist:
                validated_data['final_reviewer'] = None
        else:
            validated_data['final_reviewer'] = None
        
        # Определяем статус и создаем цепочку согласования
        if approvers:
            validated_data['status'] = 'send_for_approve'
        else:
            validated_data['status'] = 'new'
        
        task = serializer.save(created_by=employee, **validated_data)
        
        # Создаем записи в цепочке согласования
        if approvers:
            for order, approver in enumerate(approvers):
                TaskApprovalChain.objects.create(
                    task=task,
                    approver=approver,
                    order=order
                )
        
        # Если есть recipients, устанавливаем их
        # Используем getlist() для QueryDict (FormData) или get() для обычного dict (JSON)
        if hasattr(self.request.data, 'getlist'):
            recipients_ids_raw = self.request.data.getlist('recipients_ids')
        else:
            recipients_ids_raw = self.request.data.get('recipients_ids', [])
        
        # Преобразуем в список целых чисел
        if not recipients_ids_raw:
            recipients_ids = []
        elif isinstance(recipients_ids_raw, str):
            recipients_ids = [int(recipients_ids_raw)]
        elif isinstance(recipients_ids_raw, list):
            recipients_ids = [int(rid) for rid in recipients_ids_raw if rid and str(rid).strip()]
        else:
            recipients_ids = []
            
        if recipients_ids:
            recipients = Employee.objects.filter(id__in=recipients_ids)
            task.recipients.set(recipients)
            # Если assigned_employee не установлен, устанавливаем первого адресата
            if not task.assigned_employee and recipients.exists():
                task.assigned_employee = recipients.first()
                task.save(update_fields=['assigned_employee'])
        
        # Создаем задачи-согласования, если нужно
        if approvers:
            first_approver = approvers[0]
            approval_task = Task.objects.create(
                task_type='task_approval',
                status='new',
                title=f"Согласование создания задачи: {task.title}",
                description=f"Требуется согласование создания задачи:\n{task.title}",
                created_by=employee,
                assigned_employee=first_approver,
                parent_task=task,
                relation_type='creation_approval',
                card=task.card,
            )
            TaskHistory.objects.create(
                task=task,
                employee=employee,
                action='sent_for_approve',
                comment=f'Задача отправлена на согласование создания ({first_approver.full_name})'
            )
            TaskHistory.objects.create(
                task=approval_task,
                employee=employee,
                action='created',
                comment=f'Задача согласования создания создана'
            )
            
            # Отправляем уведомление первому согласующему
            try:
                from .notifications import send_task_notification
                creator_name = employee.full_name if employee.full_name else employee.user.get_full_name() or employee.user.username
                send_task_notification(
                    user=first_approver.user,
                    title="Требуется согласование",
                    body=f"{creator_name} отправил(-а) поручение «{task.title}» на согласование",
                    task_id=approval_task.id,
                    notification_type='task.approval_required'
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка отправки уведомления согласующему: {e}")
        else:
            # Если нет согласующих, создаем историю и отправляем уведомление исполнителю
            if task.assigned_employee:
                # Создаем запись в истории
                TaskHistory.objects.create(
                    task=task,
                    employee=employee,
                    action='created',
                    comment=f'Задача создана и назначена {task.assigned_employee.full_name}'
                )
                
                # Отправляем уведомление исполнителю
                try:
                    from .notifications import send_task_notification
                    creator_name = employee.full_name if employee.full_name else employee.user.get_full_name() or employee.user.username
                    send_task_notification(
                        user=task.assigned_employee.user,
                        title="Новая задача",
                        body=f"{creator_name} назначил(-а) вам задачу: {task.title}",
                        task_id=task.id,
                        notification_type='task.created'
                    )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Ошибка отправки уведомления исполнителю: {e}")
        
        # Создаем вложения (файл и/или ссылка)
        from .models import TaskAttachment
        if file:
            TaskAttachment.objects.create(
                task=task,
                file=file,
                uploaded_by=employee
            )
        if google_drive_link:
            TaskAttachment.objects.create(
                task=task,
                link=google_drive_link,
                uploaded_by=employee
            )

    def update(self, request, *args, **kwargs):
        """Обновление задачи (включая изменение статуса через drag-and-drop)"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        try:
            employee = request.user.employee
        except Employee.DoesNotExist:
            return Response(
                {'error': 'У пользователя нет связанного сотрудника'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        effective_employee = employee.get_effective_employee()
        
        # Проверяем права на редактирование
        can_edit = False
        
        # Разрешаем редактирование создателю задачи только если статус revision
        if instance.status == 'revision' and instance.created_by == effective_employee:
            can_edit = True
        
        # Также разрешаем редактирование через drag-and-drop (изменение статуса)
        # и другим стандартным способам, если они уже были разрешены
        if not can_edit:
            # Проверяем стандартные права доступа
            if effective_employee.role in ("director", "deputy"):
                can_edit = True
            elif effective_employee.role == "head" and effective_employee.department:
                can_edit = (
                    instance.created_by == effective_employee or
                    instance.assigned_employee == effective_employee or
                    effective_employee in instance.recipients.all() or
                    (instance.assigned_department == effective_employee.department) or
                    (instance.assigned_employee and instance.assigned_employee.department == effective_employee.department)
                )
            else:
                can_edit = (
                    instance.created_by == effective_employee or
                    instance.assigned_employee == effective_employee or
                    effective_employee in instance.recipients.all()
                )
        
        if not can_edit:
            return Response(
                {'error': 'У вас нет прав на редактирование этой задачи'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Если создатель редактирует задачу в статусе revision,
        # обрабатываем специальным образом
        is_creator_editing_revision = (
            instance.status == 'revision' and 
            instance.created_by == effective_employee
        )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Если создатель редактирует задачу в статусе revision
        if is_creator_editing_revision:
            # Определяем, были ли изменения в содержимом задачи
            changed_fields = []
            if 'title' in request.data and request.data['title'] != instance.title:
                changed_fields.append('название')
            if 'description' in request.data and request.data['description'] != instance.description:
                changed_fields.append('описание')
            if 'due_date' in request.data:
                new_due_date = request.data['due_date']
                old_due_date_str = str(instance.due_date) if instance.due_date else None
                if new_due_date != old_due_date_str:
                    changed_fields.append('срок выполнения')
            if 'priority' in request.data and request.data['priority'] != instance.priority:
                changed_fields.append('приоритет')
            
            # Сохраняем изменения
            self.perform_update(serializer)
            
            # Обновляем instance из БД для получения актуальных данных
            instance.refresh_from_db()
            
            # Меняем статус на send_for_approve
            instance.status = 'send_for_approve'
            
            # Определяем цепочку согласующих (используем существующую или определяем новую)
            approvers = []
            existing_chain = instance.approval_chain.all()
            
            if existing_chain.exists():
                # Используем существующую цепочку
                approvers = [ac.approver for ac in existing_chain.order_by('order')]
            else:
                # Определяем новую цепочку на основе параметров задачи
                approvers = self._determine_approvers(
                    instance.created_by,
                    instance.is_according_to_plan,
                    None  # deputy_id не сохраняется в задаче, используем None
                )
            
            # Запускаем цепочку согласований
            if approvers:
                # Удаляем старые незавершенные задачи на согласование для этой задачи
                Task.objects.filter(
                    parent_task=instance,
                    task_type='task_approval',
                    status__in=['new', 'in_progress']
                ).delete()
                
                # Очищаем старую цепочку и создаем новую
                instance.approval_chain.all().delete()
                for order, approver in enumerate(approvers, 1):
                    instance.add_to_approval_chain(approver, order=order)
                
                # Создаем задачу для первого согласующего
                first_approver = approvers[0]
                
                approval_task = Task.objects.create(
                    task_type='task_approval',
                    status='new',
                    title=f"Согласование создания задачи: {instance.title}",
                    description=f"Требуется согласование создания задачи:\n\n{instance.title}",
                    created_by=instance.created_by,
                    assigned_employee=first_approver,
                    parent_task=instance,
                    relation_type='creation_approval',
                    card=instance.card,
                )
                
                TaskHistory.objects.create(
                    task=instance,
                    employee=effective_employee,
                    action='sent_for_approve',
                    comment=f'Задача отправлена на согласование создания ({first_approver.full_name})'
                )
                TaskHistory.objects.create(
                    task=approval_task,
                    employee=effective_employee,
                    action='created',
                    comment=f'Задача согласования создания создана'
                )
            else:
                # Нет согласующих - просто меняем статус на new
                instance.status = 'new'
                instance.approval_chain.all().delete()
                TaskHistory.objects.create(
                    task=instance,
                    employee=effective_employee,
                    action='updated',
                    comment='Задача отредактирована и готова к выполнению'
                )
            
            instance.save()
            
            # Создаем запись в истории об изменениях
            if changed_fields:
                TaskHistory.objects.create(
                    task=instance,
                    employee=effective_employee,
                    action='updated',
                    comment=f'Задача отредактирована: изменено {", ".join(changed_fields)}'
                )
        else:
            # Обычное обновление - если меняется статус, создаём запись в истории
            if 'status' in request.data and request.data['status'] != instance.status:
                TaskHistory.objects.create(
                    task=instance,
                    employee=effective_employee,
                    action='assigned' if request.data['status'] == 'in_progress' else request.data['status'],
                )
            
            self.perform_update(serializer)
        
        # Возвращаем обновленную задачу
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Удаление задачи - только для статуса revision и только для создателя"""
        instance = self.get_object()
        
        try:
            employee = request.user.employee
        except Employee.DoesNotExist:
            return Response(
                {'error': 'У пользователя нет связанного сотрудника'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        effective_employee = employee.get_effective_employee()
        
        # Проверяем, что задача в статусе revision
        if instance.status != 'revision':
            return Response(
                {'error': 'Задачу можно удалить только в статусе "На пересмотрении"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, что пользователь - создатель задачи
        if instance.created_by != effective_employee:
            return Response(
                {'error': 'Только создатель задачи может её удалить'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Удаляем связанные задачи на согласование, если они есть
        with transaction.atomic():
            Task.objects.filter(
                parent_task=instance,
                task_type='task_approval'
            ).delete()
            
            # Удаляем задачу
            instance.delete()
        
        return Response(
            {'message': 'Задача успешно удалена'},
            status=status.HTTP_204_NO_CONTENT
        )


class EventCardViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = CardPagination

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EventCardDetailSerializer
        return EventCardSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        try:
            employee = self.request.user.employee
        except Employee.DoesNotExist:
            return EventCard.objects.none()

        effective_employee = employee.get_effective_employee()
        
        # Директор и заместитель видят все карточки
        if effective_employee.role in ("director", "deputy"):
            queryset = EventCard.objects.all()
        else:
            # Карточки с visible=True - видят все
            # Карточки с visible=False - видят только:
            # 1. Ответственный отдел (responsible_department)
            # 2. Смежные отделы (shared_departments)
            access_filter = Q(visible=True)  # Все видят карточки с visible=True
            
            # Для карточек с visible=False - только свой отдел и смежные
            if effective_employee.department:
                hidden_access = (
                    Q(visible=False) &
                    (Q(responsible_department=effective_employee.department) |
                     Q(shared_departments=effective_employee.department))
                )
                access_filter |= hidden_access
            
            # Для страницы согласования плана: при retrieve разрешаем доступ к карточке,
            # если у пользователя есть задача на согласование плана по этой карточке (руководитель другого отдела)
            if self.action == 'retrieve':
                approval_card_ids = Task.objects.filter(
                    assigned_employee=effective_employee,
                    task_type='approval',
                    card__isnull=False
                ).values_list('card_id', flat=True).distinct()
                access_filter |= Q(id__in=approval_card_ids)
            
            queryset = EventCard.objects.filter(access_filter).distinct()

        queryset = queryset.select_related(
            'created_by', 'responsible_department', 'final_approver'
        ).prefetch_related('categories', 'shared_departments', 'tasks', 'approvers')

        # Для retrieve/update/partial_update не применяем фильтры по категории и архиву:
        # карточку нужно найти по ID (в т.ч. при редактировании дат в архиве).
        if self.action in ('retrieve', 'update', 'partial_update'):
            return queryset.order_by('-start_date')

        category = self.request.query_params.get('category')

        if category:
            queryset = queryset.filter(categories__slug=category)

        # Фильтр по принадлежности: "Мой отдел" — ответственный или смежный
        scope = self.request.query_params.get('scope', 'all')
        if scope == 'my_department' and effective_employee.department:
            queryset = queryset.filter(
                Q(responsible_department=effective_employee.department) |
                Q(shared_departments=effective_employee.department)
            ).distinct()

        # Для директора и заместителя: фильтр по отделу (карточки, где отдел — ответственный или смежный)
        department_id = self.request.query_params.get('department_id')
        if department_id and effective_employee.role in ('director', 'deputy'):
            try:
                dept = Department.objects.get(id=department_id)
                queryset = queryset.filter(
                    Q(responsible_department=dept) | Q(shared_departments=dept)
                ).distinct()
            except (Department.DoesNotExist, ValueError):
                pass

        # Фильтрация по активности карточек
        archive = self.request.query_params.get('archive', 'false').lower() == 'true'
        today = timezone.now().date()
        
        if archive:
            # Показываем только архивные карточки (end_date < сегодня)
            queryset = queryset.filter(end_date__lt=today)
        else:
            # Показываем активные и будущие карточки (end_date >= сегодня или end_date is null)
            queryset = queryset.filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            )

        return queryset.order_by('-start_date')

    def perform_create(self, serializer):
        from django.db import transaction
        
        employee = self.request.user.employee
        
        # Получаем approvers_ids из request.data и передаём в serializer
        approvers_ids = self.request.data.getlist('approvers_ids', []) or []
        if not approvers_ids:
            approvers_ids = self.request.data.get('approvers_ids', []) or []
        
        # Преобразуем в список целых чисел
        approvers_ids = [int(id) for id in approvers_ids if id]
        
        with transaction.atomic():
            # Сохраняем карточку с approvers_ids
            card = serializer.save(created_by=employee, approvers_ids=approvers_ids)
            
            # Определяем статус карточки в зависимости от наличия плана
            if card.has_plan and card.plan_file:
                card.plan_status = "pending"
                card.plan_submitted_at = timezone.now()
                card.visible = False
            else:
                card.plan_status = "draft"
                card.visible = True
            
            card.save(update_fields=['plan_status', 'plan_submitted_at', 'visible'])
            
            # Создаём первую задачу на согласование / утверждение, если есть план
            if card.has_plan and card.plan_file:
                approver_orders = CardApproverOrder.objects.filter(card=card).order_by("order")
                
                if approver_orders.exists():
                    # Есть согласующие → первая задача идёт первому
                    first_approver = approver_orders.first().employee
                    card.current_approver_index = 0
                    card.save(update_fields=["current_approver_index"])
                    
                    approval_task = Task.objects.create(
                        title=f"Согласовать план мероприятия «{card.title}»",
                        description="Необходимо рассмотреть загруженный план и утвердить или отклонить.",
                        card=card,
                        assigned_employee=first_approver,
                        created_by=employee,
                        task_type="approval",
                        priority="urgent",
                    )
                    
                    # Отправляем уведомление согласующему
                    try:
                        from .notifications import send_task_notification
                        creator_name = employee.full_name if employee.full_name else employee.user.get_full_name() or employee.user.username
                        send_task_notification(
                            user=first_approver.user,
                            title="Требуется согласование плана",
                            body=f"{creator_name} отправил(-а) план мероприятия «{card.title}» на согласование",
                            task_id=approval_task.id,
                            notification_type='task.plan_approval_required'
                        )
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Ошибка отправки уведомления согласующему плана: {e}")
                elif card.final_approver:
                    # Нет согласующих → сразу финальному утверждающему
                    existing_task = Task.objects.filter(
                        card=card,
                        task_type="approval",
                        assigned_employee=card.final_approver
                    ).exists()
                    
                    if not existing_task:
                        approval_task = Task.objects.create(
                            title=f"Утвердить план мероприятия «{card.title}»",
                            description="Необходимо рассмотреть загруженный план и утвердить или отклонить.",
                            card=card,
                            assigned_employee=card.final_approver,
                            created_by=employee,
                            task_type="approval",
                            priority="normal",
                        )
                        
                        # Отправляем уведомление финальному утверждающему
                        try:
                            from .notifications import send_task_notification
                            creator_name = employee.full_name if employee.full_name else employee.user.get_full_name() or employee.user.username
                            send_task_notification(
                                user=card.final_approver.user,
                                title="Требуется согласование плана",
                                body=f"{creator_name} отправил(-а) план мероприятия «{card.title}» на согласование",
                                task_id=approval_task.id,
                                notification_type='task.plan_approval_required'
                            )
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Ошибка отправки уведомления финальному утверждающему плана: {e}")
                    
                    card.current_approver_index = 0
                    card.save(update_fields=["current_approver_index"])

    def perform_update(self, serializer):
        """Только создатель, директор или заместитель могут редактировать мероприятие"""
        card = serializer.instance
        try:
            employee = self.request.user.employee
        except Employee.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('У вас нет прав на редактирование мероприятия')

        effective_employee = employee.get_effective_employee()
        can_edit = (
            card.created_by == effective_employee or
            effective_employee.role in ('director', 'deputy')
        )
        if not can_edit:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Редактирование доступно только создателю, директору или заместителю')

        super().perform_update(serializer)


class EmployeeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Отключаем пагинацию для сотрудников

    def get_queryset(self):
        return Employee.objects.select_related('user', 'department').all()
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Добавляем photo_url для каждого сотрудника
        if response.data:
            # Без пагинации response.data будет списком
            employees_data = response.data if isinstance(response.data, list) else response.data.get('results', [])
            for employee_data in employees_data:
                employee_id = employee_data.get('id')
                if employee_id:
                    try:
                        employee = Employee.objects.get(id=employee_id)
                        if employee.photo:
                            employee_data['photo_url'] = request.build_absolute_uri(employee.photo.url)
                        else:
                            employee_data['photo_url'] = None
                    except Employee.DoesNotExist:
                        employee_data['photo_url'] = None
        return response
    
    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        # Добавляем photo_url для сотрудника
        if response.data:
            employee_id = response.data.get('id')
            if employee_id:
                try:
                    employee = Employee.objects.get(id=employee_id)
                    if employee.photo:
                        response.data['photo_url'] = request.build_absolute_uri(employee.photo.url)
                    else:
                        response.data['photo_url'] = None
                except Employee.DoesNotExist:
                    response.data['photo_url'] = None
        return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def take_task_view(request, task_id):
    """Взять задачу в работу"""
    from .models import TaskHistory
    from django.shortcuts import get_object_or_404
    from django.db import transaction
    import re
    
    task = get_object_or_404(Task, id=task_id)
    employee = request.user.employee
    effective_employee = employee.get_effective_employee()

    if task.assigned_employee and task.assigned_employee != effective_employee:
        return Response(
            {'error': 'Эта задача уже назначена другому сотруднику'},
            status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        task.assigned_employee = effective_employee
        task.status = 'in_progress'
        task.save()

        TaskHistory.objects.create(
            task=task,
            employee=effective_employee,
            action='taken',
        )

        # Если это задача на проверку (review), обновляем статус исходной задачи
        if task.task_type == 'review':
            # Ищем исходную задачу через parent_task
            base_task = task.parent_task

            if base_task:
                base_task.status = "under_review"
                base_task.save(update_fields=["status"])
                TaskHistory.objects.create(
                    task=base_task,
                    employee=effective_employee,
                    action="under_review",
                    comment="На проверке"
                )
                
                # Отправляем WebSocket уведомление исполнителю исходной задачи
                if base_task.assigned_employee and base_task.assigned_employee.user != request.user:
                    try:
                        from .notifications import send_task_notification
                        reviewer_name = effective_employee.full_name if effective_employee.full_name else effective_employee.user.username
                        send_task_notification(
                            user=base_task.assigned_employee.user,
                            title="Исполнение принято на проверку",
                            body=f"{employee.full_name} принял(-а) исполнение вашей задачи {base_task.title} на проверку",
                            task_id=base_task.id,
                            notification_type='task.review_taken'
                        )
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Ошибка отправки уведомления при взятии задачи на проверку: {e}")
        
        # Если это задача согласования создания (task_approval), обновляем статус основной задачи
        if task.task_type == 'task_approval':
            main_task = task.parent_task
            if main_task and main_task.status == 'send_for_approve':
                main_task.status = 'pending'
                main_task.save(update_fields=['status'])
                TaskHistory.objects.create(
                    task=main_task,
                    employee=effective_employee,
                    action='pending',
                    comment='Принята на согласование'
                )

    return Response(TaskSerializer(task).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_task_view(request, task_id):
    """
    Завершить задачу (старый endpoint, оставлен для совместимости).
    Исполнитель помечает задачу как выполненную без прохождения проверки.
    """
    from .models import TaskHistory
    from django.shortcuts import get_object_or_404

    task = get_object_or_404(Task, id=task_id)
    employee = request.user.employee

    if task.assigned_employee != employee:
        return Response(
            {'error': 'Вы не можете выполнить эту задачу'},
            status=status.HTTP_403_FORBIDDEN
        )

    task.status = 'done'
    task.completed_at = timezone.now()
    task.save()

    TaskHistory.objects.create(
        task=task,
        employee=employee,
        action='done',
    )

    # Уведомление создателю задачи: исполнитель завершил задачу (без проверки).
    # Отправляется только если создатель не совпадает с исполнителем.
    if task.created_by and task.created_by.user and task.created_by.user != request.user:
        try:
            from .notifications import send_task_notification
            executor_name = employee.full_name if employee.full_name else employee.user.get_full_name() or employee.user.username
            send_task_notification(
                user=task.created_by.user,
                title="Задача завершена",
                body=f"{executor_name} завершил(-а) задачу «{task.title}»",
                task_id=task.id,
                notification_type='task.completed'
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка отправки уведомления создателю о завершении задачи: {e}")

    return Response(TaskSerializer(task).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_task_view(request, task_id):
    """
    Исполнение задачи:
    - Исполнитель добавляет описание, ссылку и файл.
    - После отправки создаётся (или обновляется) задача типа 'review' для проверяющего.
    - Задача переходит в статус 'sent_for_review'.
    """
    from .models import TaskHistory, TaskAttachment
    from django.shortcuts import get_object_or_404
    from django.db import transaction
    import re
    
    task = get_object_or_404(Task, id=task_id)
    employee = request.user.employee

    # Проверка доступа
    if task.assigned_employee != employee:
        return Response(
            {'error': 'Вы не можете выполнить эту задачу'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Если задача уже на рассмотрении — запрет редактирования
    if task.status == "under_review":
        return Response(
            {'error': 'Задача уже на рассмотрении и не может быть изменена'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Проверяем, не взята ли задача на проверку в работу
    if task.status == "sent_for_review":
        # Ищем задачу на проверку
        review_task = (
            Task.objects.filter(
                parent_task=task,
                task_type="review",
                assigned_employee=task.created_by,
                relation_type='execution_review'
            )
            .order_by("-created_at")
            .first()
        )
        
        # Если задача на проверку уже взята в работу, запрещаем редактирование
        if review_task and review_task.status == "in_progress":
            return Response(
                {'error': 'Задача уже на рассмотрении и не может быть изменена'},
                status=status.HTTP_400_BAD_REQUEST
            )

    description = request.data.get('execution_comment', '').strip()
    file = request.FILES.get('file')
    link = request.data.get('link', '').strip()

    def _copy_package_to_review_task(review_task_obj, package_attachments):
        """Копируем пакет вложений в задачу проверки."""
        review_task_obj.attachments.all().delete()
        for src in package_attachments:
            TaskAttachment.objects.create(
                task=review_task_obj,
                file=src.file if src.file else None,
                link=src.link if src.link else None,
                uploaded_by=src.uploaded_by
            )

    with transaction.atomic():
        # Формируем цепочку проверяющих:
        # 1) Цепочка перенаправлений (в обратном порядке)
        # 2) Если review_self — создатель задачи
        # 3) Если указан final_reviewer — финальный проверяющий
        reviewers_list = []
        
        redirect_chain_entries = task.redirect_chain.all().order_by('order')
        if redirect_chain_entries.exists():
            for entry in reversed(list(redirect_chain_entries)):
                reviewers_list.append(entry.from_employee)
        
        if getattr(task, 'review_self', True):
            reviewers_list.append(task.created_by)
        
        if getattr(task, 'final_reviewer', None):
            reviewers_list.append(task.final_reviewer)

        # Если проверяющих нет вообще — сразу завершаем задачу без проверки
        if not reviewers_list:
            # История: выполнение принято без проверки
            TaskHistory.objects.create(
                task=task,
                employee=employee,
                action="done",
                comment=description or "Задача выполнена без проверки."
            )
            # Вложения (для истории, даже без проверки)
            if file:
                TaskAttachment.objects.create(task=task, file=file, uploaded_by=employee)
            if link:
                TaskAttachment.objects.create(task=task, link=link, uploaded_by=employee)

            task.status = "done"
            task.completed_at = timezone.now()
            task.save(update_fields=["status", "completed_at"])
            return Response(TaskSerializer(task).data)

        # Если проверяющие есть — обычная логика отправки на проверку
        if task.status == "sent_for_review":
            action_label = "execution_updated"
            comment_text = description or "Исполнитель внёс изменения в выполнение."
        else:
            action_label = "sent_for_review"
            comment_text = description or "Отправлено на проверку"

        exec_history = TaskHistory.objects.create(
            task=task,
            employee=employee,
            action=action_label,
            comment=comment_text
        )

        # Вложения должны относиться к этому действию исполнения,
        # поэтому сохраняем их после записи в историю
        submission_attachment_ids = []
        if file:
            a = TaskAttachment.objects.create(task=task, file=file, uploaded_by=employee)
            submission_attachment_ids.append(a.id)
        if link:
            a = TaskAttachment.objects.create(task=task, link=link, uploaded_by=employee)
            submission_attachment_ids.append(a.id)

        submission_attachments = task.attachments.filter(id__in=submission_attachment_ids).order_by("uploaded_at")

        task.status = "sent_for_review"
        task.save(update_fields=["status"])

        # Создаем цепочку проверяющих в новой модели
        task.review_chain.all().delete()
        for order, reviewer in enumerate(reviewers_list, 1):
            task.add_to_review_chain(reviewer, order=order)
        
        # Ищем существующую задачу на проверку для первого проверяющего
        first_reviewer = reviewers_list[0] if reviewers_list else None
        existing_review = (
            Task.objects.filter(
                parent_task=task,
                task_type="review",
                assigned_employee=first_reviewer,
                relation_type='execution_review'
            )
            .order_by("-created_at")
            .first()
        ) if first_reviewer else None
        
        if first_reviewer and (not existing_review or existing_review.status == "done"):
            # Создаем только первую задачу на проверку для первого проверяющего
            review_task = Task.objects.create(
                title=f"Проверить выполнение задачи «{task.title}»",
                description=description,
                card=task.card,
                assigned_employee=first_reviewer,
                created_by=employee,
                parent_task=task,
                relation_type='execution_review',
                task_type="review",
                status="new",
                priority="normal",
            )
            
            TaskHistory.objects.create(
                task=review_task,
                employee=employee,
                action="created",
                comment=f"Создана задача для проверки выполнения. Проверяющий: {first_reviewer.full_name}."
            )

            # Первый проверяющий видит пакет исполнителя этой отправки
            if submission_attachment_ids:
                _copy_package_to_review_task(review_task, submission_attachments)
            
            # Отправляем уведомление проверяющему
            try:
                from .notifications import send_task_notification
                executor_name = employee.full_name if employee.full_name else employee.user.get_full_name() or employee.user.username
                send_task_notification(
                    user=first_reviewer.user,
                    title="Исполнение на проверке",
                    body=f"{executor_name} отправил(-а) исполнение задачи: «{task.title}» на проверку",
                    task_id=review_task.id,
                    notification_type='task.execution_sent_for_review'
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка отправки уведомления проверяющему: {e}")
        else:
            # Если review ещё не завершена — просто обновляем её
            if existing_review:
                existing_review.description = (
                    f"Исполнитель обновил выполнение задачи.\n\n{description or existing_review.description}"
                )
                existing_review.status = "new"
                existing_review.save(update_fields=["description", "status"])
                
                TaskHistory.objects.create(
                    task=existing_review,
                    employee=employee,
                    action="execution_updated",
                    comment="Исполнитель обновил выполнение."
                )

                # Обновляем пакет вложений для текущего проверяющего.
                # Если исполнитель не приложил новых данных, оставляем предыдущий пакет.
                if submission_attachment_ids:
                    _copy_package_to_review_task(existing_review, submission_attachments)

    return Response(TaskSerializer(task).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def redirect_task_view(request, task_id):
    """
    Перенаправление задачи:
    - Заместитель может перенаправить любому сотруднику
    - Руководитель отдела может перенаправить сотрудникам своего отдела
    - Задача перенаправляется новому исполнителю
    - Создается запись в истории
    """
    from .models import TaskHistory
    from django.shortcuts import get_object_or_404
    from django.db import transaction
    
    task = get_object_or_404(Task, id=task_id)
    employee = request.user.employee
    
    # Проверка доступа - только исполнитель может перенаправить
    if task.assigned_employee != employee:
        return Response(
            {'error': 'Вы не можете перенаправить эту задачу'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Проверка роли - только заместитель или руководитель отдела могут перенаправить
    if employee.role not in ('deputy', 'head'):
        return Response(
            {'error': 'Только заместитель или руководитель отдела могут перенаправить задачу'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Проверка типа задачи - можно перенаправить только обычные задачи
    if task.task_type != 'regular':
        return Response(
            {'error': 'Можно перенаправить только обычные задачи'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверка статуса - можно перенаправить только новую задачу или задачу в работе
    if task.status not in ('new', 'in_progress'):
        return Response(
            {'error': 'Можно перенаправить только новую задачу или задачу в работе'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    new_employee_id = request.data.get('employee_id')
    if not new_employee_id:
        return Response(
            {'error': 'Не указан новый исполнитель'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        new_employee = Employee.objects.get(id=new_employee_id)
    except Employee.DoesNotExist:
        return Response(
            {'error': 'Новый исполнитель не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Проверка прав на перенаправление
    if employee.role == 'head':
        # Руководитель может перенаправить только сотрудникам своего отдела
        if not employee.department or new_employee.department != employee.department:
            return Response(
                {'error': 'Руководитель может перенаправить задачу только сотрудникам своего отдела'},
                status=status.HTTP_403_FORBIDDEN
            )
    # Заместитель может перенаправить любому сотруднику (проверка не нужна)
    
    with transaction.atomic():
        # Сохраняем информацию о перенаправлении в новую модель
        order = task.redirect_chain.aggregate(max_order=Max('order'))['max_order'] or 0
        order += 1
        
        # Добавляем текущее перенаправление в цепочку
        task.redirect_chain.create(
            from_employee=employee,
            to_employee=new_employee,
            order=order,
            reason=request.data.get('reason', '')
        )
        
        # Обновляем основные поля задачи
        task.redirected_by = employee
        task.assigned_employee = new_employee
        task.status = 'new'  # Задача становится новой для нового исполнителя
        task.save(update_fields=['redirected_by', 'assigned_employee', 'status'])
        
        # Обновляем recipients
        task.recipients.clear()
        task.recipients.add(new_employee)
        
        # Создаем запись в истории
        TaskHistory.objects.create(
            task=task,
            employee=employee,
            action='redirected',
            comment=f'Задача перенаправлена от {employee.full_name} к {new_employee.full_name}'
        )
        
        # Отправляем уведомление новому исполнителю
        try:
            from .notifications import send_task_notification
            redirector_name = employee.full_name if employee.full_name else employee.user.get_full_name() or employee.user.username
            send_task_notification(
                user=new_employee.user,
                title="Задача перенаправлена",
                body=f"{redirector_name} перенаправил(-а) вам задачу «{task.title}» на исполнение",
                task_id=task.id,
                notification_type='task.redirected'
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка отправки уведомления при перенаправлении задачи: {e}")
    
    # Перезагружаем задачу с правильными связями для сериализации
    task.refresh_from_db()
    task = Task.objects.select_related(
        'created_by', 'assigned_employee', 'assigned_department', 'card', 'redirected_by'
    ).prefetch_related('recipients', 'history').get(id=task.id)
    
    return Response(TaskSerializer(task, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def return_redirect_task_view(request, task_id):
    """
    Вернуть перенаправленную задачу себе (забрать у текущего исполнителя).
    Доступно только тому, кто перенаправил задачу (redirected_by), и только если задача ещё не принята в работу (статус new).
    """
    from .models import TaskHistory
    from django.shortcuts import get_object_or_404
    from django.db import transaction

    task = get_object_or_404(Task, id=task_id)
    employee = request.user.employee

    if task.redirected_by != employee:
        return Response(
            {'error': 'Вернуть задачу может только тот, кто её перенаправил'},
            status=status.HTTP_403_FORBIDDEN
        )

    if task.status != 'new':
        return Response(
            {'error': 'Вернуть можно только задачу, которая ещё не принята в работу'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if task.task_type != 'regular':
        return Response(
            {'error': 'Вернуть можно только обычные задачи'},
            status=status.HTTP_400_BAD_REQUEST
        )

    previous_assignee = task.assigned_employee

    with transaction.atomic():
        # Получаем цепочку перенаправлений и удаляем последнюю запись
        redirect_chain = task.redirect_chain.all().order_by('-order')
        if redirect_chain.exists():
            last_redirect = redirect_chain.first()
            last_redirect.delete()
            
            # Проверяем, есть ли еще перенаправления
            remaining_redirect = task.redirect_chain.all().order_by('-order').first()
            new_redirected_by = remaining_redirect.from_employee if remaining_redirect else None
        else:
            new_redirected_by = None

        task.assigned_employee = employee
        task.redirected_by = new_redirected_by
        task.status = 'new'
        task.save(update_fields=['assigned_employee', 'redirected_by', 'status'])

        task.recipients.clear()
        task.recipients.add(employee)

        TaskHistory.objects.create(
            task=task,
            employee=employee,
            action='return_redirect',
            comment=f'Задача возвращена от {previous_assignee.full_name} к {employee.full_name}'
        )

        try:
            from .notifications import send_task_notification
            redirector_name = employee.full_name or employee.user.get_full_name() or employee.user.username
            if previous_assignee and previous_assignee.user:
                send_task_notification(
                    user=previous_assignee.user,
                    title='Задача возвращена',
                    body=f'{redirector_name} вернул(-а) себе задачу «{task.title}»',
                    task_id=task.id,
                    notification_type='task.return_redirect'
                )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Ошибка уведомления при возврате задачи: {e}')

    task.refresh_from_db()
    task = Task.objects.select_related(
        'created_by', 'assigned_employee', 'assigned_department', 'card', 'redirected_by'
    ).prefetch_related('recipients', 'history').get(id=task.id)

    return Response(TaskSerializer(task, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def categories_view(request):
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def departments_view(request):
    # Сортируем отделы по приоритету (меньше = выше), затем по имени
    departments = Department.objects.all().order_by('priority', 'name')
    serializer = DepartmentSerializer(departments, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_task_attachment(request, task_id):
    """Загрузить вложение к задаче"""
    from .models import TaskAttachment
    from django.shortcuts import get_object_or_404
    
    task = get_object_or_404(Task, id=task_id)
    employee = request.user.employee
    
    file = request.FILES.get('file')
    link = request.data.get('link', '').strip()
    
    if file:
        attachment = TaskAttachment.objects.create(
            task=task,
            file=file,
            uploaded_by=employee
        )
    elif link:
        attachment = TaskAttachment.objects.create(
            task=task,
            link=link,
            uploaded_by=employee
        )
    else:
        return Response(
            {'error': 'Необходимо указать файл или ссылку'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    from .serializers import TaskAttachmentSerializer
    return Response(TaskAttachmentSerializer(attachment).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_plan_view(request, task_id):
    """
    Согласование плана мероприятия:
    - текущий согласующий утверждает;
    - создаётся задача для следующего согласующего (если есть);
    - финальный утверждающий утверждает окончательно.
    """
    from django.shortcuts import get_object_or_404
    from django.db import transaction
    
    task = get_object_or_404(Task, id=task_id)
    employee = request.user.employee
    effective_employee = employee.get_effective_employee()
    
    if task.task_type != "approval":
        return Response(
            {'error': 'Это не задача на согласование'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    card = task.card
    if not card:
        return Response(
            {'error': 'У задачи не указана карточка'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    approver_orders = CardApproverOrder.objects.filter(card=card).order_by("order")
    approvers = [rel.employee for rel in approver_orders]
    total_approvers = len(approvers)
    
    if not approvers and not card.final_approver:
        return Response(
            {'error': 'У карточки не настроен процесс согласования'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверяем, что текущий сотрудник — согласующий или утверждающий
    current_order = next((rel for rel in approver_orders if rel.employee == effective_employee), None)
    is_final_approver = card.final_approver == effective_employee
    
    if not current_order and not is_final_approver:
        return Response(
            {'error': 'Вы не являетесь согласующим для этого плана'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Проверяем, что задача назначена текущему сотруднику
    if task.assigned_employee != effective_employee:
        return Response(
            {'error': 'Эта задача назначена другому сотруднику'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    with transaction.atomic():
        # Завершаем текущую задачу
        task.status = "done"
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at"])
        
        TaskHistory.objects.create(
            task=task,
            employee=effective_employee,
            action="approved"
        )
        
        # Если финальный утверждающий утверждает окончательно
        if is_final_approver:
            card.plan_status = "approved"
            card.plan_approved_at = timezone.now()
            card.visible = True
            card.is_fully_approved = True
            card.current_approver_index = total_approvers + 1
            card.save(update_fields=[
                "plan_status", "plan_approved_at", "visible", "is_fully_approved", "current_approver_index"
            ])
            
            # Отправляем уведомление автору карточки об утверждении
            if card.created_by and card.created_by.user:
                try:
                    from .notifications import send_task_notification
                    approver_name = effective_employee.full_name if effective_employee.full_name else effective_employee.user.get_full_name() or effective_employee.user.username
                    send_task_notification(
                        user=card.created_by.user,
                        title="План мероприятия утвержден",
                        body=f"{approver_name} утвердил(а) ваш план мероприятия «{card.title}»",
                        task_id=task.id,
                        notification_type='task.plan_approved',
                        url=f"/cards/{card.id}"
                    )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Ошибка отправки уведомления автору об утверждении плана: {e}")
        else:
            # Проверяем, есть ли следующий согласующий
            current_index = current_order.order
            next_order = approver_orders.filter(order=current_index + 1).first()
            
            if next_order:
                # Есть следующий согласующий
                next_emp = next_order.employee
                card.current_approver_index = current_index + 1
                card.save(update_fields=["current_approver_index"])
                
                # Проверяем, не создана ли уже задача для следующего согласующего
                existing_task = Task.objects.filter(
                    card=card,
                    task_type="approval",
                    assigned_employee=next_emp,
                    status__in=["new", "in_progress"]
                ).exists()
                
                if not existing_task:
                    next_task = Task.objects.create(
                        title=f"Согласовать план мероприятия «{card.title}»",
                        description="Необходимо рассмотреть загруженный план и утвердить или отклонить.",
                        card=card,
                        assigned_employee=next_emp,
                        created_by=card.created_by,
                        task_type="approval",
                        priority="urgent",
                    )
                    
                    # Отправляем уведомление следующему согласующему
                    try:
                        from .notifications import send_task_notification
                        sender_name = card.created_by.full_name if card.created_by.full_name else card.created_by.user.get_full_name() or card.created_by.user.username
                        send_task_notification(
                            user=next_emp.user,
                            title="Требуется согласование плана",
                            body=f"{sender_name} отправил(а) план мероприятия «{card.title}» на согласование",
                            task_id=next_task.id,
                            notification_type='task.plan_approval_required'
                        )
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Ошибка отправки уведомления следующему согласующему плана: {e}")
            else:
                # Все согласующие завершили. Проверяем, есть ли финальный утверждающий
                if card.final_approver:
                    # Есть финальный утверждающий - создаем задачу для него
                    card.current_approver_index = total_approvers
                    card.save(update_fields=["current_approver_index"])
                    
                    # Проверяем, не создана ли уже задача для финального утверждающего
                    existing_task = Task.objects.filter(
                        card=card,
                        task_type="approval",
                        assigned_employee=card.final_approver,
                        status__in=["new", "in_progress"]
                    ).exists()
                    
                    if not existing_task:
                        final_task = Task.objects.create(
                            title=f"Утвердить план мероприятия «{card.title}»",
                            description="Необходимо рассмотреть загруженный план и утвердить или отклонить.",
                            card=card,
                            assigned_employee=card.final_approver,
                            created_by=card.created_by,
                            task_type="approval",
                            priority="urgent",
                        )
                        
                        # Отправляем уведомление финальному утверждающему
                        try:
                            from .notifications import send_task_notification
                            sender_name = card.created_by.full_name if card.created_by.full_name else card.created_by.user.get_full_name() or card.created_by.user.username
                            send_task_notification(
                                user=card.final_approver.user,
                                title="Требуется согласование плана",
                                body=f"{sender_name} отправил(а) план мероприятия «{card.title}» на утверждение",
                                task_id=final_task.id,
                                notification_type='task.plan_approval_required'
                            )
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Ошибка отправки уведомления финальному утверждающему плана: {e}")
                    # НЕ утверждаем план здесь - только финальный утверждающий может это сделать
                else:
                    # Если финального утверждающего нет, завершаем полностью
                    card.plan_status = "approved"
                    card.plan_approved_at = timezone.now()
                    card.visible = True
                    card.is_fully_approved = True
                    card.current_approver_index = total_approvers
                    card.save(update_fields=[
                        "plan_status", "plan_approved_at", "visible", "is_fully_approved", "current_approver_index"
                    ])
                    
                    # Отправляем уведомление автору карточки об утверждении
                    if card.created_by and card.created_by.user:
                        try:
                            from .notifications import send_task_notification
                            approver_name = effective_employee.full_name if effective_employee.full_name else effective_employee.user.get_full_name() or effective_employee.user.username
                            send_task_notification(
                                user=card.created_by.user,
                                title="План мероприятия утвержден",
                                body=f"{approver_name} утвердил(а) ваш план мероприятия «{card.title}»",
                                task_id=task.id,
                                notification_type='task.plan_approved',
                                url=f"/cards/{card.id}"
                            )
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Ошибка отправки уведомления автору об утверждении плана: {e}")
    
    return Response({
        'task': TaskSerializer(task).data,
        'card': EventCardSerializer(card).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_plan_view(request, task_id):
    """Отклонить план мероприятия"""
    from django.shortcuts import get_object_or_404
    from django.db import transaction
    
    task = get_object_or_404(Task, id=task_id)
    employee = request.user.employee
    effective_employee = employee.get_effective_employee()
    
    if task.task_type != "approval":
        return Response(
            {'error': 'Это не задача на согласование'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    card = task.card
    if not card:
        return Response(
            {'error': 'У задачи не указана карточка'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    reason = request.data.get('reason', '').strip()
    
    if not reason:
        return Response(
            {'error': 'Укажите причину отклонения'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверяем, что задача назначена текущему сотруднику
    if task.assigned_employee != effective_employee:
        return Response(
            {'error': 'Эта задача назначена другому сотруднику'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Получаем исправленный план, если он загружен
    corrected_plan_file = request.FILES.get('corrected_plan_file', None)
    
    with transaction.atomic():
        # Завершаем текущую задачу
        task.status = "done"
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at"])
        
        TaskHistory.objects.create(
            task=task,
            employee=effective_employee,
            action="rejected",
            comment=reason
        )
        
        # Отклоняем план
        card.plan_status = "rejected"
        card.plan_rejected_reason = reason
        card.visible = False
        
        # Если загружен исправленный план, обновляем файл
        if corrected_plan_file:
            card.plan_file = corrected_plan_file
        
        card.save(update_fields=["plan_status", "plan_rejected_reason", "visible", "plan_file"])
        
        # Отправляем уведомление автору карточки об отклонении
        if card.created_by and card.created_by.user:
            try:
                from .notifications import send_task_notification
                rejector_name = effective_employee.full_name if effective_employee.full_name else effective_employee.user.get_full_name() or effective_employee.user.username
                send_task_notification(
                    user=card.created_by.user,
                    title="План мероприятия отклонен",
                    body=f"{rejector_name} отклонил(а) ваш план мероприятия «{card.title}»",
                    task_id=task.id,
                    notification_type='task.plan_rejected',
                    url=f"/cards/{card.id}"
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка отправки уведомления автору об отклонении плана: {e}")
    
    return Response({
        'task': TaskSerializer(task).data,
        'card': EventCardSerializer(card).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def card_approvers_view(request, card_id):
    """Получить список согласующих карточки"""
    from django.shortcuts import get_object_or_404
    
    card = get_object_or_404(EventCard, id=card_id)
    approver_orders = CardApproverOrder.objects.filter(card=card).order_by("order")
    
    approvers_data = []
    for rel in approver_orders:
        approvers_data.append({
            'id': rel.id,
            'employee': EmployeeSerializer(rel.employee).data,
            'order': rel.order
        })
    
    return Response(approvers_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_plan_file_view(request, card_id):
    """Скачать файл плана мероприятия с заголовком Content-Disposition: attachment"""
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return Response(
            {'error': 'У пользователя нет связанного сотрудника'},
            status=status.HTTP_404_NOT_FOUND
        )

    card = get_object_or_404(EventCard, id=card_id)

    # Та же логика доступа, что и в EventCardViewSet.get_queryset()
    effective_employee = employee.get_effective_employee()
    if effective_employee.role in ("director", "deputy"):
        allowed_ids = EventCard.objects.values_list('id', flat=True)
    else:
        access_filter = Q(visible=True)
        if effective_employee.department:
            hidden_access = (
                Q(visible=False) &
                (Q(responsible_department=effective_employee.department) |
                 Q(shared_departments=effective_employee.department))
            )
            access_filter |= hidden_access
        allowed_ids = EventCard.objects.filter(access_filter).distinct().values_list('id', flat=True)

    # Дополнительно разрешаем скачивание, если у пользователя есть задача на согласование плана по этой карточке
    if card.id not in allowed_ids:
        has_approval_task = Task.objects.filter(
            card_id=card.id,
            assigned_employee=effective_employee,
            task_type='approval'
        ).exists()
        if not has_approval_task:
            return Response(
                {'error': 'Нет доступа к этой карточке'},
                status=status.HTTP_404_NOT_FOUND
            )

    if not card.plan_file:
        return Response(
            {'error': 'Файл плана не найден'},
            status=status.HTTP_404_NOT_FOUND
        )

    file_path = card.plan_file.path
    filename = (os.path.basename(card.plan_file.name) or os.path.basename(file_path) or 'plan').strip()
    if not filename:
        filename = 'plan'
    # Сохраняем расширение из реального файла, если в имени его нет
    _, ext = os.path.splitext(os.path.basename(file_path))
    if ext and not os.path.splitext(filename)[1]:
        filename = filename.rstrip('.') + ext

    content_type, _ = mimetypes.guess_type(filename)
    if content_type:
        response = FileResponse(open(file_path, 'rb'), content_type=content_type, as_attachment=True, filename=filename)
    else:
        response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)

    # RFC 5987: ASCII fallback + UTF-8 для кириллицы и спецсимволов
    ext = os.path.splitext(filename)[1]
    has_non_ascii = filename != filename.encode('ascii', 'ignore').decode('ascii')
    if has_non_ascii:
        ascii_fallback = 'plan' + (ext if ext else '')
        response['Content-Disposition'] = f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{quote(filename)}'
    else:
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_corrected_plan_view(request, card_id):
    """Загрузка исправленного плана после отклонения"""
    from django.shortcuts import get_object_or_404
    
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return Response(
            {'error': 'У пользователя нет связанного сотрудника'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    card = get_object_or_404(EventCard, id=card_id)
    
    # Проверяем, что план был отклонен
    if card.plan_status != 'rejected':
        return Response(
            {'error': 'План не был отклонен. Загрузка исправленного плана доступна только для отклоненных планов.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверяем, что пользователь является создателем карточки
    if card.created_by != employee:
        return Response(
            {'error': 'Только создатель карточки может загрузить исправленный план'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Получаем файл исправленного плана
    corrected_plan_file = request.FILES.get('corrected_plan_file')
    if not corrected_plan_file:
        return Response(
            {'error': 'Необходимо загрузить файл исправленного плана'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    with transaction.atomic():
        # Обновляем файл плана
        card.plan_file = corrected_plan_file
        card.plan_status = 'pending'
        card.plan_submitted_at = timezone.now()
        card.plan_rejected_reason = None  # Сбрасываем причину отклонения
        card.visible = False
        card.current_approver_index = 0  # Сбрасываем индекс согласующего
        
        # Удаляем старые задачи на согласование для этой карточки
        Task.objects.filter(
            card=card,
            task_type='approval',
            status__in=['new', 'in_progress', 'rejected']
        ).delete()
        
        # Создаём новую задачу на согласование
        approver_orders = CardApproverOrder.objects.filter(card=card).order_by("order")
        
        if approver_orders.exists():
            # Есть согласующие → первая задача идёт первому
            first_approver = approver_orders.first().employee
            card.current_approver_index = 0
            
            approval_task = Task.objects.create(
                title=f"Согласовать план мероприятия «{card.title}»",
                description="Необходимо рассмотреть исправленный план и утвердить или отклонить.",
                card=card,
                assigned_employee=first_approver,
                created_by=employee,
                task_type="approval",
                priority="urgent",
            )
            
            # Отправляем уведомление первому согласующему
            try:
                from .notifications import send_task_notification
                sender_name = employee.full_name if employee.full_name else employee.user.get_full_name() or employee.user.username
                send_task_notification(
                    user=first_approver.user,
                    title="Требуется согласование плана",
                    body=f"{sender_name} отправил(-а) план мероприятия «{card.title}» на согласование",
                    task_id=approval_task.id,
                    notification_type='task.plan_approval_required',
                    url=f"/cards/{card.id}"
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка отправки уведомления первому согласующему при загрузке исправленного плана: {e}")
        elif card.final_approver:
            # Нет согласующих → сразу финальному утверждающему
            approval_task = Task.objects.create(
                title=f"Утвердить план мероприятия «{card.title}»",
                description="Необходимо рассмотреть исправленный план и утвердить или отклонить.",
                card=card,
                assigned_employee=card.final_approver,
                created_by=employee,
                task_type="approval",
                priority="urgent",
            )
            
            # Отправляем уведомление финальному утверждающему
            try:
                from .notifications import send_task_notification
                sender_name = employee.full_name if employee.full_name else employee.user.get_full_name() or employee.user.username
                send_task_notification(
                    user=card.final_approver.user,
                    title="Требуется согласование плана",
                    body=f"{sender_name} отправил(-а) план мероприятия «{card.title}» на утверждение",
                    task_id=approval_task.id,
                    notification_type='task.plan_approval_required',
                    url=f"/cards/{card.id}"
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка отправки уведомления финальному утверждающему при загрузке исправленного плана: {e}")
        
        card.save(update_fields=['plan_file', 'plan_status', 'plan_submitted_at', 'plan_rejected_reason', 'visible', 'current_approver_index'])
    
    return Response({
        'message': 'Исправленный план успешно загружен и отправлен на повторное согласование',
        'card': EventCardSerializer(card).data
    })


# Новые API endpoints для проверки задач

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_review_view(request, task_id):
    """
    Страница проверки выполнения задачи.
    Возвращает данные для отображения: исходную задачу, вложения, комментарии.
    """
    from django.shortcuts import get_object_or_404
    import re
    
    review_task = get_object_or_404(Task, id=task_id)
    reviewer = request.user.employee
    effective_reviewer = reviewer.get_effective_employee()

    # Проверка доступа
    if review_task.assigned_employee != effective_reviewer and effective_reviewer.role not in ("director", "deputy"):
        return Response(
            {'error': 'У вас нет доступа к этой задаче'},
            status=status.HTTP_403_FORBIDDEN
        )

    if review_task.task_type != "review":
        return Response(
            {'error': 'Это не задача на согласование исполнения'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Ищем исходную задачу через parent_task
    base_task = review_task.parent_task

    if not base_task:
        return Response(
            {'error': 'Исходная задача не найдена'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Собираем данные
    attachments = []
    last_exec_comment = None

    # Ищем последнюю отправку на согласование исполнителем
    last_exec = base_task.history.filter(
        action__in=["sent_for_review", "execution_updated"]
    ).order_by("-timestamp").first()

    if last_exec:
        last_exec_comment = last_exec.comment

    # Основной источник вложений для проверки — пакет, прикрепленный к review-задаче.
    attachments = review_task.attachments.all().order_by("uploaded_at")

    # Fallback для старых задач (до внедрения пакетной передачи вложений):
    # первый проверяющий увидит вложения исполнителя последней отправки.
    if (not attachments.exists()) and review_task.created_by_id == base_task.assigned_employee_id and last_exec:
        attachments = (
            base_task.attachments
            .filter(uploaded_at__gte=last_exec.timestamp)
            .order_by("uploaded_at")
        )

    from .serializers import TaskSerializer, TaskAttachmentSerializer

    return Response({
        'review_task': TaskSerializer(review_task).data,
        'base_task': TaskSerializer(base_task).data,
        'attachments': TaskAttachmentSerializer(attachments, many=True).data,
        'last_exec_comment': last_exec_comment,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def task_review_approve_view(request, task_id):
    """Проверяющий утверждает выполнение задачи."""
    from .models import TaskHistory, TaskAttachment
    from django.shortcuts import get_object_or_404
    from django.db import transaction
    import re
    
    review_task = get_object_or_404(Task, id=task_id)
    reviewer = request.user.employee
    effective_reviewer = reviewer.get_effective_employee()

    # Проверка доступа
    if review_task.assigned_employee != effective_reviewer:
        return Response(
            {'error': 'Вы не можете утвердить эту задачу'},
            status=status.HTTP_403_FORBIDDEN
        )

    if review_task.task_type != "review":
        return Response(
            {'error': 'Это не задача на согласование'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Ищем исходную задачу через parent_task
    base_task = review_task.parent_task

    if not base_task:
        return Response(
            {'error': 'Исходная задача не найдена'},
            status=status.HTTP_404_NOT_FOUND
        )

    comment = request.data.get('comment', '').strip()
    file = request.FILES.get('file')
    link = request.data.get('link', '').strip()
    approve_with_changes = request.data.get('approve_with_changes', False)
    if isinstance(approve_with_changes, str):
        approve_with_changes = approve_with_changes.lower() in ('true', '1', 'yes')

    if approve_with_changes and not file and not link:
        return Response(
            {'error': 'Для утверждения с поправками добавьте файл или ссылку'},
            status=status.HTTP_400_BAD_REQUEST
        )

    def _copy_attachments(src_attachments, target_task, uploaded_by):
        """Копирует вложения (пакет) из одной review-задачи в другую."""
        target_task.attachments.all().delete()
        for src in src_attachments:
            TaskAttachment.objects.create(
                task=target_task,
                file=src.file if src.file else None,
                link=src.link if src.link else None,
                uploaded_by=uploaded_by
            )

    def _get_latest_file_and_link(attachments_qs):
        latest_file = attachments_qs.filter(file__isnull=False).order_by("-uploaded_at").first()
        latest_link = attachments_qs.filter(link__isnull=False).order_by("-uploaded_at").first()
        return latest_file, latest_link
    with transaction.atomic():
        # Обновляем статусы
        review_task.status = "done"
        review_task.save(update_fields=["status"])
        TaskHistory.objects.create(
            task=review_task,
            employee=effective_reviewer,
            action="approved",
            comment=comment or "Проверка выполнена, задача утверждена."
        )

        # Находим текущего проверяющего в цепочке и отмечаем как одобрившего
        review_entries = base_task.review_chain.all().order_by('order')
        current_review_entry = review_entries.filter(reviewer=effective_reviewer, status='pending').first()
        
        if current_review_entry:
            # Отмечаем текущего проверяющего как одобрившего
            current_review_entry.status = 'approved'
            current_review_entry.reviewed_at = timezone.now()
            current_review_entry.review_comment = comment
            current_review_entry.save(update_fields=['status', 'reviewed_at', 'review_comment'])

        current_package = review_task.attachments.all().order_by("uploaded_at")
        
        # Ищем следующего проверяющего
        next_review_entry = review_entries.filter(status='pending', order__gt=current_review_entry.order if current_review_entry else -1).first() if current_review_entry else review_entries.filter(status='pending').first()
        
        if next_review_entry:
            # Есть еще проверяющие
            next_reviewer = next_review_entry.reviewer
            
            # Проверяем, нет ли уже задачи на проверку для следующего проверяющего
            existing_review = Task.objects.filter(
                parent_task=base_task,
                task_type="review",
                assigned_employee=next_reviewer,
                relation_type='execution_review'
            ).exclude(id=review_task.id).order_by("-created_at").first()
            
            if not existing_review or existing_review.status == "done":
                # Создаем новую задачу на проверку для следующего проверяющего
                # Создатель - текущий проверяющий (не исполнитель!)
                next_review_task = Task.objects.create(
                    title=f"Проверить выполнение задачи «{base_task.title}»",
                    description=(
                        f"{review_task.description or ''}"
                    ),
                    card=base_task.card,
                    assigned_employee=next_reviewer,
                    created_by=effective_reviewer,  # Создатель - текущий проверяющий
                    parent_task=base_task,
                    relation_type='execution_review',
                    task_type="review",
                    status="new",
                    priority="normal",
                )

                # Формируем пакет вложений для следующего проверяющего
                if approve_with_changes:
                    # С поправками: измененное поле перезаписывает текущее,
                    # неизмененное — переносится с предыдущего шага.
                    prev_file, prev_link = _get_latest_file_and_link(current_package)

                    if file:
                        TaskAttachment.objects.create(task=next_review_task, file=file, uploaded_by=effective_reviewer)
                    elif prev_file:
                        TaskAttachment.objects.create(task=next_review_task, file=prev_file.file, uploaded_by=effective_reviewer)

                    if link:
                        TaskAttachment.objects.create(task=next_review_task, link=link, uploaded_by=effective_reviewer)
                    elif prev_link:
                        TaskAttachment.objects.create(task=next_review_task, link=prev_link.link, uploaded_by=effective_reviewer)
                else:
                    # Без поправок: передаем пакет как есть.
                    _copy_attachments(current_package, next_review_task, effective_reviewer)
                
                TaskHistory.objects.create(
                    task=base_task,
                    employee=effective_reviewer,
                    action='pending',
                    comment=(
                        f'Проверка передана {next_reviewer.full_name}'
                        + (' с поправками.' if approve_with_changes else '.')
                    )
                )
                # Уведомление следующему проверяющему
                if next_reviewer.user:
                    try:
                        from .notifications import send_task_notification
                        reviewer_name = effective_reviewer.full_name or (effective_reviewer.user.get_full_name() if effective_reviewer.user else '') or getattr(effective_reviewer.user, 'username', '')
                        send_task_notification(
                            user=next_reviewer.user,
                            title="Передано на вашу проверку",
                            body=f"{reviewer_name} отправил(-а) исполнение задачи «{base_task.title}» на проверку"
                            + (" (с поправками)." if approve_with_changes else "."),
                            task_id=next_review_task.id,
                            notification_type='task.execution_sent_for_review'
                        )
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Ошибка отправки уведомления следующему проверяющему: {e}")
            else:
                # Если задача на следующего проверяющего уже есть и активна — обновляем пакет вложений.
                if approve_with_changes:
                    prev_file, prev_link = _get_latest_file_and_link(current_package)
                    existing_review.attachments.all().delete()
                    if file:
                        TaskAttachment.objects.create(task=existing_review, file=file, uploaded_by=effective_reviewer)
                    elif prev_file:
                        TaskAttachment.objects.create(task=existing_review, file=prev_file.file, uploaded_by=effective_reviewer)
                    if link:
                        TaskAttachment.objects.create(task=existing_review, link=link, uploaded_by=effective_reviewer)
                    elif prev_link:
                        TaskAttachment.objects.create(task=existing_review, link=prev_link.link, uploaded_by=effective_reviewer)
                else:
                    _copy_attachments(current_package, existing_review, effective_reviewer)
                # Уведомление следующему проверяющему (задача уже была создана, обновлён пакет)
                if next_reviewer.user:
                    try:
                        from .notifications import send_task_notification
                        reviewer_name = effective_reviewer.full_name or (effective_reviewer.user.get_full_name() if effective_reviewer.user else '') or getattr(effective_reviewer.user, 'username', '')
                        send_task_notification(
                            user=next_reviewer.user,
                            title="Передано на вашу проверку",
                            body=f"{reviewer_name} отправил(-а) исполнение задачи «{base_task.title}» на проверку"
                            + (" (с поправками)." if approve_with_changes else "."),
                            task_id=existing_review.id,
                            notification_type='task.execution_sent_for_review'
                        )
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Ошибка отправки уведомления следующему проверяющему: {e}")
        else:
            # Нет больше проверяющих - завершаем исходную задачу
            base_task.status = "done"
            base_task.review_comment = comment or "Задача утверждена без комментария."
            base_task.save(update_fields=["status", "review_comment"])
            TaskHistory.objects.create(
                task=base_task,
                employee=effective_reviewer,
                action="done",
                comment=comment or "Задача проверена и утверждена всеми проверяющими."
            )
            # Уведомление исполнителю: выполнение задачи утверждено последним проверяющим
            if base_task.assigned_employee and base_task.assigned_employee.user:
                try:
                    from .notifications import send_task_notification
                    reviewer_name = effective_reviewer.full_name if effective_reviewer.full_name else effective_reviewer.user.get_full_name() or effective_reviewer.user.username
                    send_task_notification(
                        user=base_task.assigned_employee.user,
                        title="Задача утверждена",
                        body=f"{reviewer_name} утвердил(-а) выполнение задачи «{base_task.title}»",
                        task_id=base_task.id,
                        notification_type='task.execution_approved'
                    )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Ошибка отправки уведомления исполнителю об утверждении: {e}")
    
    from .serializers import TaskSerializer
    return Response(TaskSerializer(base_task).data if base_task else TaskSerializer(review_task).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def task_review_reject_view(request, task_id):
    """Проверяющий возвращает задачу на доработку."""
    from .models import TaskHistory
    from django.shortcuts import get_object_or_404
    from django.db import transaction
    import re
    
    review_task = get_object_or_404(Task, id=task_id)
    reviewer = request.user.employee
    effective_reviewer = reviewer.get_effective_employee()

    # Проверка доступа
    if review_task.assigned_employee != effective_reviewer:
        return Response(
            {'error': 'Вы не можете вернуть эту задачу на доработку'},
            status=status.HTTP_403_FORBIDDEN
        )

    if review_task.task_type != "review":
        return Response(
            {'error': 'Это не задача на согласование'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Ищем исходную задачу через parent_task
    base_task = review_task.parent_task

    comment = request.data.get('comment', '').strip()
    
    if not comment:
        return Response(
            {'error': 'Укажите причину возврата на доработку'},
            status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        # Обновляем статусы
        review_task.status = "done"
        review_task.save(update_fields=["status"])
        TaskHistory.objects.create(
            task=review_task,
            employee=effective_reviewer,
            action="rejected",
            comment=comment
        )

        if base_task:
            base_task.status = "rejected"
            base_task.review_comment = comment
            base_task.save(update_fields=["status", "review_comment"])
            TaskHistory.objects.create(
                task=base_task,
                employee=effective_reviewer,
                action="rejected",
                comment=comment
            )
            # Уведомление исполнителю: выполнение возвращено на доработку
            if base_task.assigned_employee and base_task.assigned_employee.user:
                try:
                    from .notifications import send_task_notification
                    reviewer_name = effective_reviewer.full_name if effective_reviewer.full_name else effective_reviewer.user.get_full_name() or effective_reviewer.user.username
                    send_task_notification(
                        user=base_task.assigned_employee.user,
                        title="Исполнение возвращено на доработку",
                        body=f"{reviewer_name} вернул(-а) выполнение задачи «{base_task.title}» на доработку",
                        task_id=base_task.id,
                        notification_type='task.execution_rejected'
                    )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Ошибка отправки уведомления исполнителю об отклонении: {e}")

    from .serializers import TaskSerializer
    return Response(TaskSerializer(base_task).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def statistics_view(request):
    """
    Статистика по задачам и мероприятиям
    Параметры:
    - employee_id: ID сотрудника
    - department_id: ID отдела
    - date_from: начальная дата (YYYY-MM-DD)
    - date_to: конечная дата (YYYY-MM-DD)
    - card_id: ID мероприятия (опционально)
    
    Права доступа:
    - Директор и заместитель: могут выбрать любой отдел/сотрудника
    - Руководитель отдела: может выбрать только свой отдел и сотрудников из него
    - Остальные: могут выбрать только свой отдел и себя
    """
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return Response(
            {'error': 'Employee profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    effective_employee = employee.get_effective_employee()
    user_role = effective_employee.role
    is_director_or_deputy = user_role in ('director', 'deputy')
    is_head = user_role == 'head'
    
    # Получаем параметры
    employee_id = request.query_params.get('employee_id')
    department_id = request.query_params.get('department_id')
    date_from_str = request.query_params.get('date_from')
    date_to_str = request.query_params.get('date_to')
    card_id = request.query_params.get('card_id')
    
    # Проверка прав доступа для отдела
    target_department = None
    if department_id and department_id.strip():  # Проверяем, что это не пустая строка
        try:
            target_department = Department.objects.get(id=department_id)
            # Руководитель и обычные сотрудники могут видеть только свой отдел
            if not is_director_or_deputy:
                if not effective_employee.department or target_department.id != effective_employee.department.id:
                    return Response(
                        {'error': 'Недостаточно прав для просмотра статистики этого отдела'},
                        status=status.HTTP_403_FORBIDDEN
                    )
        except Department.DoesNotExist:
            return Response(
                {'error': 'Отдел не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    elif not is_director_or_deputy:
        # Если отдел не указан и пользователь не директор/заместитель, используем отдел текущего пользователя
        target_department = effective_employee.department
    # Если отдел не указан и пользователь директор/заместитель, target_department остается None - будет "все отделы"
    
    # Проверка прав доступа для сотрудника
    target_employee = None
    if employee_id and employee_id.strip():  # Проверяем, что это не пустая строка
        try:
            target_employee = Employee.objects.get(id=employee_id)
            # Обычные сотрудники могут видеть только себя
            if not is_director_or_deputy and not is_head:
                if target_employee.id != effective_employee.id:
                    return Response(
                        {'error': 'Недостаточно прав для просмотра статистики этого сотрудника'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            # Руководитель может видеть только сотрудников своего отдела
            elif is_head:
                if not target_department or target_employee.department != target_department:
                    return Response(
                        {'error': 'Недостаточно прав для просмотра статистики этого сотрудника'},
                        status=status.HTTP_403_FORBIDDEN
                    )
        except Employee.DoesNotExist:
            return Response(
                {'error': 'Сотрудник не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    # Если сотрудник не указан, target_employee остается None - будет фильтрация по отделу или "все сотрудники"
    
    # Обработка дат
    date_from = None
    date_to = None
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
            # Добавляем время конца дня
            date_to = datetime.combine(date_to, datetime.max.time())
            date_to = timezone.make_aware(date_to)
        except ValueError:
            pass
    
    # Если даты не указаны, используем текущий месяц
    if not date_from or not date_to:
        today = timezone.now().date()
        date_from = today.replace(day=1)
        # Последний день месяца
        if today.month == 12:
            date_to = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            date_to = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        date_to = datetime.combine(date_to, datetime.max.time())
        date_to = timezone.make_aware(date_to)
    
    date_from_start = timezone.make_aware(datetime.combine(date_from, datetime.min.time()))
    
    # Фильтруем задачи
    tasks_qs = Task.objects.all()
    
    # Фильтр по карточке
    if card_id:
        try:
            card = EventCard.objects.get(id=card_id)
            tasks_qs = tasks_qs.filter(card=card)
        except EventCard.DoesNotExist:
            pass
    
    # Фильтр по дате создания
    tasks_qs = tasks_qs.filter(created_at__gte=date_from_start, created_at__lte=date_to)
    
    # Фильтр по сотруднику или отделу
    if target_employee:
        # Если указан конкретный сотрудник, фильтруем по нему
        tasks_qs = tasks_qs.filter(
            Q(assigned_employee=target_employee) |
            Q(recipients=target_employee)
        ).distinct()
    elif target_department:
        # Если указан отдел (но не сотрудник), фильтруем по отделу
        tasks_qs = tasks_qs.filter(
            Q(assigned_department=target_department) |
            Q(assigned_employee__department=target_department)
        ).distinct()
    # Если и сотрудник, и отдел не указаны (target_employee = None, target_department = None),
    # то для директора/заместителя это означает "все" - не фильтруем по отделу/сотруднику
    # Оставляем все задачи (уже отфильтрованные по дате и карточке)
    
    # Статистика по задачам
    total_tasks = tasks_qs.count()
    tasks_by_status = tasks_qs.values('status').annotate(count=Count('id'))
    tasks_by_type = tasks_qs.values('task_type').annotate(count=Count('id'))
    tasks_by_priority = tasks_qs.values('priority').annotate(count=Count('id'))
    
    done_tasks = tasks_qs.filter(status='done').count()
    in_progress_tasks = tasks_qs.filter(status='in_progress').count()
    new_tasks = tasks_qs.filter(status='new').count()
    
    # Статистика по мероприятиям
    cards_qs = EventCard.objects.all()
    
    # Фильтр по дате
    date_to_date = date_to.date() if hasattr(date_to, 'date') else date_to
    cards_qs = cards_qs.filter(
        Q(start_date__lte=date_to_date) &
        (Q(end_date__gte=date_from) | Q(end_date__isnull=True))
    )
    
    # Если указана карточка, фильтруем только её
    if card_id:
        try:
            cards_qs = cards_qs.filter(id=card_id)
        except (ValueError, EventCard.DoesNotExist):
            cards_qs = EventCard.objects.none()
    else:
        # Фильтр по сотруднику или отделу для карточек
        if target_employee:
            cards_qs = cards_qs.filter(
                Q(created_by=target_employee) |
                Q(tasks__assigned_employee=target_employee) |
                Q(responsible_department=target_employee.department)
            ).distinct()
        elif target_department:
            cards_qs = cards_qs.filter(
                Q(responsible_department=target_department) |
                Q(shared_departments=target_department) |
                Q(tasks__assigned_department=target_department)
            ).distinct()
        # Если и сотрудник, и отдел не указаны (target_employee = None, target_department = None),
        # то для директора/заместителя это означает "все" - не фильтруем по отделу/сотруднику
        # Оставляем все карточки (уже отфильтрованные по дате)
    
    total_cards = cards_qs.count()
    
    # Статистика по карточкам (количество задач в них)
    cards_with_tasks = cards_qs.annotate(
        tasks_count=Count('tasks', filter=Q(tasks__created_at__gte=date_from_start, tasks__created_at__lte=date_to)),
        done_tasks_count=Count('tasks', filter=Q(tasks__status='done', tasks__created_at__gte=date_from_start, tasks__created_at__lte=date_to))
    )
    
    # Формируем ответ
    date_to_for_response = date_to.date() if hasattr(date_to, 'date') else date_to
    result = {
        'period': {
            'from': date_from.isoformat(),
            'to': date_to_for_response.isoformat() if hasattr(date_to_for_response, 'isoformat') else date_to_str
        },
        'tasks': {
            'total': total_tasks,
            'by_status': {item['status']: item['count'] for item in tasks_by_status},
            'by_type': {item['task_type']: item['count'] for item in tasks_by_type},
            'by_priority': {item['priority']: item['count'] for item in tasks_by_priority},
            'done': done_tasks,
            'in_progress': in_progress_tasks,
            'new': new_tasks,
        },
        'events': {
            'total': total_cards,
        }
    }
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_creation_view(request, task_id):
    """Согласование создания задачи"""
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return Response(
            {'error': 'У пользователя нет связанного сотрудника'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    effective_employee = employee.get_effective_employee()
    
    # Получаем задачу-согласование
    approval_task = get_object_or_404(Task, id=task_id, task_type='task_approval')
    
    # Проверяем права
    if approval_task.assigned_employee.get_effective_employee() != effective_employee:
        return Response(
            {'error': 'У вас нет прав на согласование этой задачи'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Получаем основную задачу
    main_task = approval_task.parent_task
    if not main_task:
        return Response(
            {'error': 'Не найдена связанная задача'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    comment = request.data.get('comment', '')
    
    with transaction.atomic():
        # Закрываем текущую задачу-согласование
        approval_task.status = 'done'
        approval_task.completed_at = timezone.now()
        approval_task.save(update_fields=['status', 'completed_at'])
        TaskHistory.objects.create(
            task=approval_task,
            employee=effective_employee,
            action='approved',
            comment=comment
        )
        
        # Проверяем, есть ли еще согласующие в цепочке
        chain_entries = main_task.approval_chain.all().order_by('order')
        current_entry = chain_entries.filter(status='pending').first()
        
        if current_entry:
            # Отмечаем текущего согласующего как одобрившего
            current_entry.status = 'approved'
            current_entry.approved_at = timezone.now()
            current_entry.save(update_fields=['status', 'approved_at'])
            
            # Ищем следующего согласующего
            next_entry = chain_entries.filter(status='pending', order__gt=current_entry.order).first()
            
            if next_entry:
                # Есть следующий согласующий
                next_approver = next_entry.approver
                
                # Убеждаемся, что основная задача остается в статусе send_for_approve
                if main_task.status != 'send_for_approve':
                    main_task.status = 'send_for_approve'
                    main_task.save(update_fields=['status'])
                
                # Создаем задачу для следующего согласующего
                next_approval_task = Task.objects.create(
                    task_type='task_approval',
                    status='new',
                    title=f"Согласование поручения: {main_task.title}",
                    description=f"Требуется согласование поручения:\n{main_task.title}",
                    created_by=main_task.created_by,
                    assigned_employee=next_approver,
                    parent_task=main_task,
                    relation_type='creation_approval',
                    card=main_task.card,
                )
                
                TaskHistory.objects.create(
                    task=main_task,
                    employee=effective_employee,
                    action='pending',
                    comment=f'Задача передана на согласование ({next_approver.full_name})'
                )
                TaskHistory.objects.create(
                    task=next_approval_task,
                    employee=effective_employee,
                    action='created',
                    comment=f'Задача согласования создания создана'
                )
                
                # Отправляем уведомление следующему согласующему
                try:
                    from .notifications import send_task_notification
                    creator_name = main_task.created_by.full_name if main_task.created_by.full_name else main_task.created_by.user.get_full_name() or main_task.created_by.user.username
                    send_task_notification(
                        user=next_approver.user,
                        title="Требуется согласование",
                        body=f"{creator_name} отправил(-а) вам поручение «{main_task.title}» на согласование",
                        task_id=next_approval_task.id,
                        notification_type='task.approval_required'
                    )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Ошибка отправки уведомления следующему согласующему: {e}")
            else:
                # Согласование завершено - все согласующие одобрили
                main_task.status = 'new'
                main_task.save(update_fields=['status'])
                
                TaskHistory.objects.create(
                    task=main_task,
                    employee=effective_employee,
                    action='created',
                    comment='Создание задачи согласовано'
                )
                
                # Отправляем уведомление автору задачи о завершении согласования
                if main_task.created_by and main_task.created_by.user:
                    try:
                        from .notifications import send_task_notification
                        send_task_notification(
                            user=main_task.created_by.user,
                            title="Поручение согласовано",
                            body=f"Создание вашего поручения «{main_task.title}» согласовано",
                            task_id=main_task.id,
                            notification_type='task.approved'
                        )
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Ошибка отправки уведомления автору о согласовании: {e}")
                
                # Закрываем все незавершенные задачи-согласования для этой задачи
                Task.objects.filter(
                    parent_task=main_task,
                    task_type='task_approval',
                    status__in=['new', 'in_progress']
                ).exclude(id=approval_task.id).update(status='done')
    
    return Response({
        'message': 'Создание задачи согласовано',
        'task': TaskSerializer(main_task).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recall_task_view(request, task_id):
    """Отзыв задачи из статуса send_for_approve или new (без цепочки согласующих) - меняет статус на revision"""
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return Response(
            {'error': 'У пользователя нет связанного сотрудника'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    effective_employee = employee.get_effective_employee()
    
    # Получаем задачу
    task = get_object_or_404(Task, id=task_id)
    
    # Проверяем, что задача типа обычная и в статусе send_for_approve или new (без цепочки согласующих)
    has_approval_chain = task.approval_chain.exists()
    if task.task_type == 'regular' and task.status == 'send_for_approve':
        # Отзыв из send_for_approve - удаляем задачи на согласование
        should_delete_approval_tasks = True
    elif task.task_type == 'regular' and task.status == 'new' and not has_approval_chain:
        # Отзыв из new (без цепочки) - просто меняем статус
        should_delete_approval_tasks = False
    else:
        return Response(
            {'error': 'Задачу можно отозвать только из статуса "Отправлено на согласование" или "Новая" (без цепочки согласующих)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверяем, что пользователь - создатель задачи
    if task.created_by != effective_employee:
        return Response(
            {'error': 'Только создатель задачи может её отозвать'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    with transaction.atomic():
        # Если были задачи на согласование - удаляем их
        if should_delete_approval_tasks:
            approval_tasks = Task.objects.filter(
                parent_task=task,
                task_type='task_approval',
                status__in=['new', 'in_progress']
            )
            
            # Создаем записи в истории для удаляемых задач
            for approval_task in approval_tasks:
                TaskHistory.objects.create(
                    task=approval_task,
                    employee=effective_employee,
                    action='rejected',
                    comment='Задача отозвана создателем'
                )
            
            # Удаляем задачи на согласование
            approval_tasks.delete()
        
        # Определяем исходный статус для правильного комментария (до изменения)
        original_status = task.status
        comment_text = 'Задача отозвана создателем для доработки'
        if original_status == 'new':
            comment_text = 'Задача переведена в статус "На пересмотрении" для доработки'
        
        # Меняем статус задачи на revision
        task.status = 'revision'
        task.save(update_fields=['status'])
        
        TaskHistory.objects.create(
            task=task,
            employee=effective_employee,
            action='revision',
            comment=comment_text
        )
    
    return Response({
        'message': 'Задача отозвана и переведена в статус "На пересмотрении"',
        'task': TaskSerializer(task, context={'request': request}).data
    })


# =========================================================
# API для уведомлений
# =========================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_list_view(request):
    """Получение списка уведомлений текущего пользователя"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_mark_read_view(request, notification_id):
    """Отметить уведомление как прочитанное"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return Response({'success': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notifications_mark_all_read_view(request):
    """Отметить все уведомления как прочитанные"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({'success': True})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def notifications_delete_read_view(request):
    """Удалить все прочитанные уведомления"""
    deleted_count = Notification.objects.filter(user=request.user, is_read=True).delete()[0]
    return Response({'success': True, 'deleted_count': deleted_count})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def creation_approval_view(request, task_id):
    """Получение данных для страницы согласования создания задачи"""
    from .serializers import TaskAttachmentSerializer
    
    approval_task = get_object_or_404(Task, id=task_id, task_type='task_approval')
    
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return Response(
            {'error': 'У пользователя нет связанного сотрудника'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    effective_employee = employee.get_effective_employee()
    
    # Проверяем права
    if approval_task.assigned_employee.get_effective_employee() != effective_employee:
        return Response(
            {'error': 'У вас нет прав на просмотр этой задачи'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Получаем основную задачу
    main_task = approval_task.parent_task
    if not main_task:
        return Response(
            {'error': 'Не найдена связанная задача'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Получаем вложения основной задачи
    attachments = main_task.attachments.all()
    
    # Сериализуем вложения с контекстом запроса для правильных URL
    attachments_data = []
    for attachment in attachments:
        serializer = TaskAttachmentSerializer(attachment, context={'request': request})
        attachments_data.append(serializer.data)
    
    return Response({
        'approval_task': TaskSerializer(approval_task, context={'request': request}).data,
        'main_task': TaskSerializer(main_task, context={'request': request}).data,
        'attachments': attachments_data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_creation_view(request, task_id):
    """Отклонение создания задачи"""
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return Response(
            {'error': 'У пользователя нет связанного сотрудника'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    effective_employee = employee.get_effective_employee()
    
    # Получаем задачу-согласование
    approval_task = get_object_or_404(Task, id=task_id, task_type='task_approval')
    
    # Проверяем права
    if approval_task.assigned_employee.get_effective_employee() != effective_employee:
        return Response(
            {'error': 'У вас нет прав на отклонение этой задачи'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Получаем основную задачу
    main_task = approval_task.parent_task
    if not main_task:
        return Response(
            {'error': 'Не найдена связанная задача'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    comment = request.data.get('comment', '')
    if not comment:
        return Response(
            {'error': 'Необходимо указать причину отклонения'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    with transaction.atomic():
        # Закрываем текущую задачу-согласование (статус done)
        approval_task.status = 'done'
        approval_task.completed_at = timezone.now() 
        approval_task.save(update_fields=['status', 'completed_at'])
        TaskHistory.objects.create(
            task=approval_task,
            employee=effective_employee,
            action='rejected',
            comment=comment
        )
        
        # Основная задача переходит в статус "На пересмотрении"
        main_task.status = 'revision'
        main_task.save(update_fields=['status'])
        
        TaskHistory.objects.create(
            task=main_task,
            employee=effective_employee,
            action='rejected',
            comment=f'Создание задачи отклонено: {comment}'
        )
        
        # Отправляем уведомление автору задачи об отклонении
        if main_task.created_by and main_task.created_by.user:
            try:
                from .notifications import send_task_notification
                rejector_name = effective_employee.full_name if effective_employee.full_name else effective_employee.user.get_full_name() or effective_employee.user.username
                send_task_notification(
                    user=main_task.created_by.user,
                    title="Создание поручения отклонено",
                    body=f"{rejector_name} отклонил(-а) создание вашего поручения «{main_task.title}»",
                    task_id=main_task.id,
                    notification_type='task.creation_rejected'
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка отправки уведомления автору об отклонении: {e}")
        
        # Закрываем все незавершенные задачи-согласования для этой задачи
        Task.objects.filter(
            parent_task=main_task,
            task_type='task_approval',
            status__in=['new', 'in_progress']
        ).exclude(id=approval_task.id).update(status='done')
    
    return Response({
        'message': 'Создание задачи отклонено',
        'task': TaskSerializer(main_task).data
    })