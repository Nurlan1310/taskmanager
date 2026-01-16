from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Q
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils import timezone

# 1. ИМПОРТ МОДЕЛЕЙ
from .models import (
    Task, TaskComment, FCMDevice, Notification, 
    Employee, TaskAttachment, Department, EventCard
)

# 2. ИМПОРТ СЕРИАЛИЗАТОРОВ
from .serializers import (
    TaskSerializer,
    TaskCommentSerializer,
    TaskAttachmentSerializer,
    FCMDeviceSerializer,
    NotificationSerializer,
    DepartmentSerializer,
    EventCardSerializer,
    EmployeeSerializer
)

from .signals import send_task_notification

# =====================================================
# 📋 ГЛАВНЫЙ СПИСОК ЗАДАЧ (Умная фильтрация и Контроль)
# =====================================================
class MyTasksApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            employee = request.user.employee
        except Employee.DoesNotExist:
            return Response({"error": "Профиль сотрудника не найден"}, status=404)

        # Параметры запроса
        view_mode = request.query_params.get('view_mode', 'my_tasks')
        card_id = request.query_params.get('card_id')
        dept_id = request.query_params.get('dept_id')
        employee_id = request.query_params.get('employee_id') # 🔥 Новое: фильтр по конкретному человеку
        for_assistant = request.query_params.get('for_assistant') == 'true'

        # 🔥 Оптимизированный запрос: Убрали exclude(status='done'), чтобы вернуть задачи во вкладку "Выполненные"
        qs = Task.objects.all().select_related(
            'assigned_employee', 'assigned_department', 'created_by', 'card'
        )

        # Логика фильтрации по ролям
        if for_assistant:
            if employee.role in ["director", "deputy"]:
                tasks = qs
            elif employee.role == "head":
                tasks = qs.filter(
                    Q(assigned_department=employee.department) |
                    Q(assigned_employee=employee) |
                    Q(created_by=employee)
                )
            else:
                tasks = qs.filter(Q(assigned_employee=employee) | Q(created_by=employee))

        elif view_mode == 'assigned_by_me':
            # 🔥 Только порученные ДРУГИМ (исключаем задачи самому себе)
            tasks = qs.filter(created_by=employee).exclude(assigned_employee=employee)

        elif view_mode == 'department':
            if employee.role in ['head', 'director', 'deputy']:
                # Если директор не выбрал отдел, показываем все задачи (как all_org)
                if not dept_id and employee.role in ['director', 'deputy']:
                    tasks = qs
                else:
                    target_dept = dept_id if dept_id else employee.department_id
                    tasks = qs.filter(
                        Q(assigned_department_id=target_dept) | 
                        Q(assigned_employee__department_id=target_dept)
                    )
            else:
                tasks = qs.filter(assigned_employee=employee)

        elif view_mode == 'all_org' and employee.role in ['director', 'deputy']:
            tasks = qs

        else:
            tasks = qs.filter(
                Q(assigned_employee=employee) | Q(recipients=employee) | Q(cc=employee)
            )

        # 🔥 Точечное добавление: Фильтр по конкретному сотруднику (для каскада)
        if employee_id:
            tasks = tasks.filter(assigned_employee_id=employee_id)

        # Фильтр по карточке (если пришел ID)
        if card_id:
            tasks = tasks.filter(card_id=card_id)

        tasks = tasks.distinct().order_by('-created_at')
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)


# =====================================================
# 🔍 ДЕТАЛИ И СМЕНА СТАТУСА (Без изменений)
# =====================================================
class TaskDetailApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        serializer = TaskSerializer(task)
        return Response(serializer.data)

    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        new_status = request.data.get("status")
        valid_statuses = ["new", "in_progress", "under_review", "done", "rejected", "sent_for_review"]

        if new_status not in valid_statuses:
            return Response({"error": "Неверный статус"}, status=400)

        task.status = new_status
        if new_status == 'done':
            task.completed_at = timezone.now()
        task.save()

        try:
            author_name = request.user.employee.full_name
        except AttributeError:
            author_name = request.user.username

        body = f"{author_name} изменил(а) статус задачи на «{task.get_status_display()}»"
        
        recipient_user = None
        if task.created_by and task.created_by.user != request.user:
            recipient_user = task.created_by.user
        elif task.assigned_employee and task.assigned_employee.user != request.user:
            recipient_user = task.assigned_employee.user

        if recipient_user:
            send_task_notification(recipient_user, "Обновление задачи", body, task.id)

        return Response({"success": True, "new_status": new_status})


# =====================================================
# 💬 КОММЕНТАРИИ И ВЛОЖЕНИЯ (Без изменений)
# =====================================================
class TaskCommentsApi(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        comments = task.comments.all().order_by('created_at')
        serializer = TaskCommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        serializer = TaskCommentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                author = request.user.employee
            except:
                return Response({"error": "Нужен профиль"}, status=400)
            serializer.save(task=task, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TaskAttachmentUploadApi(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        serializer = TaskAttachmentSerializer(data=request.data)
        if serializer.is_valid():
            try: employee = request.user.employee
            except: return Response({"error": "Профиль не найден"}, status=400)
            serializer.save(task=task, uploaded_by=employee)
            body = f"{employee.full_name} добавил(а) файл в задачу «{task.title}»"
            if task.created_by and task.created_by.user != request.user:
                send_task_notification(task.created_by.user, "Новое вложение", body, task.id)
            return Response({"success": True, "file": serializer.data})
        return Response(serializer.errors, status=400)


# =====================================================
# 🔔 УВЕДОМЛЕНИЯ И FCM (ФИНАЛЬНЫЙ ФИКС)
# =====================================================
class NotificationListApi(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = Notification.objects.filter(user=request.user).order_by("-created_at")
        serializer = NotificationSerializer(qs, many=True)
        return Response(serializer.data)

class NotificationMarkReadApi(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, notification_id):
        n = get_object_or_404(Notification, id=notification_id, user=request.user)
        n.is_read = True
        n.save(update_fields=["is_read"])
        return Response({"success": True})

class NotificationMarkAllReadApi(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"success": True})

class FCMRegisterApi(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # 🔥 БЕРЕМ ДАННЫЕ НАПРЯМУЮ (БЕЗ СЕРИАЛИЗАТОРА)
            # Это самый надежный способ, если сериализатор глючит или отбрасывает поля
            data = request.data
            token = data.get("token")
            platform = data.get("platform", "android")

            # На случай, если в базе или библиотеке поле называется registration_id
            if not token:
                token = data.get("registration_id")

            # Проверка
            if not token:
                print(f"❌ ОШИБКА: Пришел запрос без токена! Данные: {data}")
                return Response({"error": "Token is required"}, status=400)

            # Сохраняем жестко, без лишних проверок
            FCMDevice.objects.update_or_create(
                token=token,
                defaults={"user": request.user, "platform": platform}
            )
            
            # Возвращаем успех
            return Response({"success": True}, status=201)

        except Exception as e:
            print(f"🔥 FCM Error: {e}")
            return Response({"error": str(e)}, status=400)

class FCMUnregisterApi(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        token = request.data.get("token")
        if not token: return Response({"error": "Токен обязателен"}, status=400)
        FCMDevice.objects.filter(token=token, user=request.user).delete()
        return Response({"success": True})


# =====================================================
# 🔑 АВТОРИЗАЦИЯ
# =====================================================
class LoginApi(APIView):
    authentication_classes = []; permission_classes = []
    def post(self, request):
        username, password = request.data.get("username"), request.data.get("password")
        user = authenticate(username=username, password=password)
        if not user: return Response({"detail": "Ошибка входа"}, status=401)
        token, _ = Token.objects.get_or_create(user=user)
        try:
            emp = user.employee
            role, dept, name = emp.role, (emp.department.name if emp.department else "Без отдела"), emp.full_name
        except: role, dept, name = "staff", "Без отдела", user.username
        return Response({"token": token.key, "full_name": name, "role": role, "department": dept})


# =====================================================
# 🛠 ФИЛЬТРЫ ДЛЯ РУКОВОДИТЕЛЕЙ (Каскадная логика)
# =====================================================
class FiltersApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = request.user.employee
        target_dept_id = request.query_params.get('dept_id')
        data = {}

        # 1. Доступные карточки (Внутренняя работа видна благодаря visible=True)
        cards = EventCard.objects.filter(
            Q(responsible_department=employee.department) |
            Q(shared_departments=employee.department) |
            Q(created_by=employee) | 
            Q(tasks__assigned_employee=employee) |
            Q(visible=True)
        ).distinct()
        data['cards'] = EventCardSerializer(cards, many=True).data

        # 2. Директор/Зам: Список отделов + Сотрудники выбранного отдела
        if employee.role in ['director', 'deputy']:
            data['departments'] = DepartmentSerializer(Department.objects.all(), many=True).data
            if target_dept_id:
                dept_staff = Employee.objects.filter(department_id=target_dept_id)
                data['dept_employees'] = EmployeeSerializer(dept_staff, many=True).data
            else:
                data['dept_employees'] = []

        # 3. Начальник: Только сотрудники его отдела
        if employee.role == 'head':
            subordinates = Employee.objects.filter(department=employee.department)
            data['my_team'] = EmployeeSerializer(subordinates, many=True).data

        return Response(data)