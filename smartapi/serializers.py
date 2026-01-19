from rest_framework import serializers
from django.contrib.auth.models import User
from tasks.models import Employee, Department


class SmartEmployeeSerializer(serializers.ModelSerializer):
    """Сериализатор для tasks_employee - возвращает ВСЕ поля"""
    department = serializers.SerializerMethodField()
    full_name = serializers.CharField(read_only=True)
    full_name_complete = serializers.CharField(read_only=True)
    delegate_to_name = serializers.SerializerMethodField()
    delegate_to_id = serializers.IntegerField(source='delegate_to.id', read_only=True, allow_null=True)
    department_id = serializers.IntegerField(source='department.id', read_only=True, allow_null=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = Employee
        fields = '__all__'  # Возвращаем все поля модели
        # Явно перечисляем все поля для ясности:
        # fields = [
        #     'id', 'user', 'user_id', 'position', 'department', 'department_id', 'role', 'role_display',
        #     'photo', 'internal_phone', 'external_phone',
        #     'firstname', 'lastname', 'middlename',
        #     'delegate_to', 'delegate_to_id', 'delegate_until',
        #     'full_name', 'full_name_complete', 'delegate_to_name'
        # ]
    
    def get_department(self, obj):
        """Возвращает полную информацию об отделе или None"""
        if obj.department:
            return {
                'id': obj.department.id,
                'name': obj.department.name,
                'priority': obj.department.priority
            }
        return None
    
    def get_delegate_to_name(self, obj):
        """Возвращает имя замещающего сотрудника или None"""
        if obj.delegate_to:
            return obj.delegate_to.full_name
        return None


class SmartUserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для auth_user - возвращает ВСЕ поля включая password
    Также добавляет ФИО из связанного Employee, если он существует
    """
    # Добавляем ФИО из Employee, если он существует
    firstname = serializers.SerializerMethodField()
    lastname = serializers.SerializerMethodField()
    middlename = serializers.SerializerMethodField()
    employee_id = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        # Возвращаем все стандартные поля User включая password
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'password',
            'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'last_login',
            'firstname', 'lastname', 'middlename', 'employee_id'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
        # password будет возвращаться как read-only (хеш)
        extra_kwargs = {
            'password': {'read_only': True}
        }
    
    def get_firstname(self, obj):
        """Возвращает имя из Employee, если существует"""
        if hasattr(obj, 'employee') and obj.employee:
            return obj.employee.firstname
        return None
    
    def get_lastname(self, obj):
        """Возвращает отчество из Employee, если существует"""
        if hasattr(obj, 'employee') and obj.employee:
            return obj.employee.lastname
        return None
    
    def get_middlename(self, obj):
        """Возвращает фамилию из Employee, если существует"""
        if hasattr(obj, 'employee') and obj.employee:
            return obj.employee.middlename
        return None
    
    def get_employee_id(self, obj):
        """Возвращает ID связанного Employee, если существует"""
        if hasattr(obj, 'employee') and obj.employee:
            return obj.employee.id
        return None


class SmartDepartmentSerializer(serializers.ModelSerializer):
    """Сериализатор для tasks_department - возвращает ВСЕ поля"""
    class Meta:
        model = Department
        fields = '__all__'  # Все поля: id, name, priority