from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from tasks.models import Employee, Department
from .serializers import SmartUserSerializer, SmartEmployeeSerializer, SmartDepartmentSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def employees_view(request):
    """
    API endpoint для получения всех сотрудников (tasks_employee)
    GET /api/smart/employees/
    Возвращает полную информацию о всех сотрудниках
    """
    employees = Employee.objects.select_related('user', 'department', 'delegate_to').all()
    serializer = SmartEmployeeSerializer(employees, many=True)
    return Response({
        'count': len(serializer.data),
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def departments_view(request):
    """
    API endpoint для получения всех отделов (tasks_department)
    GET /api/smart/departments/
    Возвращает полную информацию о всех отделах
    """
    departments = Department.objects.all().order_by('priority', 'name')
    serializer = SmartDepartmentSerializer(departments, many=True)
    return Response({
        'count': len(serializer.data),
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def users_view(request):
    """
    API endpoint для получения пользователей (auth_user)
    Возвращает только: id, username, last_name, email, first_name, middle_name
    GET /api/smart/users/
    """
    users = User.objects.all().order_by('id')
    serializer = SmartUserSerializer(users, many=True)
    return Response({
        'count': len(serializer.data),
        'results': serializer.data
    })